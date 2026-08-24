"""Product validation for OCR pipeline definitions."""

from docmind_api.application.ocr_pipelines.config_schema import config_schema_diagnostics
from docmind_api.application.ocr_pipelines.diagnostics import error_diagnostic
from docmind_api.application.ocr_pipelines.secret_config import secret_config_diagnostics
from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineBlockCatalog,
    OcrPipelineBlockMetadata,
    OcrPipelineBlockStatus,
    OcrPipelineDiagnostic,
    OcrPipelineDiagnosticSeverity,
    OcrPipelineDraftDefinition,
    OcrPipelineStepDefinition,
)

_REQUIRED_PHASE1_STEP_TYPES = ("preflight", "ocr_parsing")


def product_diagnostics(
    *,
    definition: OcrPipelineDraftDefinition,
    catalog: OcrPipelineBlockCatalog,
) -> tuple[OcrPipelineDiagnostic, ...]:
    """Return local product validation diagnostics for one draft definition."""

    diagnostics: list[OcrPipelineDiagnostic] = []
    blocks = catalog.by_implementation_id()
    seen_step_ids: set[str] = set()
    produced_artifacts: set[str] = set()
    enabled_step_types: list[str] = []
    enabled_ocr_step_count = 0

    if not definition.steps:
        diagnostics.append(
            error_diagnostic(
                "PIPELINE_STEPS_REQUIRED",
                "OCR pipeline validation requires at least one step.",
                path="steps",
            ),
        )

    for index, step in enumerate(definition.steps):
        diagnostics.extend(
            _step_diagnostics(
                step=step,
                step_index=index,
                blocks=blocks,
                seen_step_ids=seen_step_ids,
                produced_artifacts=produced_artifacts,
                enabled_step_types=enabled_step_types,
            ),
        )
        block = blocks.get(step.implementation_id)
        if block is not None and step.enabled and block.step_type == "ocr_parsing":
            enabled_ocr_step_count += 1

    diagnostics.extend(
        _required_phase_diagnostics(
            enabled_step_types=enabled_step_types,
            enabled_ocr_step_count=enabled_ocr_step_count,
        ),
    )
    return tuple(diagnostics)


def _step_diagnostics(
    *,
    step: OcrPipelineStepDefinition,
    step_index: int,
    blocks: dict[str, OcrPipelineBlockMetadata],
    seen_step_ids: set[str],
    produced_artifacts: set[str],
    enabled_step_types: list[str],
) -> tuple[OcrPipelineDiagnostic, ...]:
    diagnostics: list[OcrPipelineDiagnostic] = []
    step_path = f"steps[{step_index}]"
    if step.step_id in seen_step_ids:
        diagnostics.append(
            error_diagnostic(
                "DUPLICATE_STEP_ID",
                "OCR pipeline step_id values must be unique.",
                path=f"{step_path}.step_id",
                step_id=step.step_id,
            ),
        )
    seen_step_ids.add(step.step_id)

    diagnostics.extend(secret_config_diagnostics(step=step, step_index=step_index))
    block = blocks.get(step.implementation_id)
    if block is None:
        diagnostics.append(
            error_diagnostic(
                "UNKNOWN_PIPELINE_BLOCK",
                "OCR pipeline step references an unknown block implementation.",
                path=f"{step_path}.implementation_id",
                step_id=step.step_id,
            ),
        )
        return tuple(diagnostics)

    diagnostics.extend(block_status_diagnostics(block=block, step=step, step_index=step_index))
    diagnostics.extend(config_schema_diagnostics(block=block, step=step, step_index=step_index))
    diagnostics.extend(_failure_policy_diagnostics(block=block, step=step, step_path=step_path))
    if step.enabled:
        enabled_step_types.append(block.step_type)
        diagnostics.extend(
            _artifact_order_diagnostics(
                block=block,
                step=step,
                step_path=step_path,
                produced_artifacts=produced_artifacts,
            ),
        )
        produced_artifacts.update(block.produces)
    return tuple(diagnostics)


def block_status_diagnostics(
    *,
    block: OcrPipelineBlockMetadata,
    step: OcrPipelineStepDefinition,
    step_index: int,
) -> tuple[OcrPipelineDiagnostic, ...]:
    """Return diagnostics for block availability."""

    path = f"steps[{step_index}].implementation_id"
    if block.status in {OcrPipelineBlockStatus.DISABLED, OcrPipelineBlockStatus.PLANNED}:
        return (
            error_diagnostic(
                "PIPELINE_BLOCK_UNAVAILABLE",
                "OCR pipeline step uses a block that is not available for publishing.",
                path=path,
                step_id=step.step_id,
            ),
        )
    if block.status == OcrPipelineBlockStatus.DEPRECATED:
        return (
            OcrPipelineDiagnostic(
                severity=OcrPipelineDiagnosticSeverity.WARNING,
                code="PIPELINE_BLOCK_DEPRECATED",
                path=path,
                step_id=step.step_id,
                message="OCR pipeline step uses a deprecated block.",
            ),
        )
    return ()


def _failure_policy_diagnostics(
    *,
    block: OcrPipelineBlockMetadata,
    step: OcrPipelineStepDefinition,
    step_path: str,
) -> tuple[OcrPipelineDiagnostic, ...]:
    if step.failure_policy in block.allowed_failure_policies:
        return ()
    return (
        error_diagnostic(
            "FAILURE_POLICY_NOT_ALLOWED",
            "OCR pipeline step uses a failure policy that is not allowed for this block.",
            path=f"{step_path}.failure_policy",
            step_id=step.step_id,
        ),
    )


def _artifact_order_diagnostics(
    *,
    block: OcrPipelineBlockMetadata,
    step: OcrPipelineStepDefinition,
    step_path: str,
    produced_artifacts: set[str],
) -> tuple[OcrPipelineDiagnostic, ...]:
    diagnostics: list[OcrPipelineDiagnostic] = []
    for artifact in block.requires:
        if artifact in produced_artifacts:
            continue
        diagnostics.append(
            error_diagnostic(
                "MISSING_REQUIRED_ARTIFACT",
                f"OCR pipeline step requires artifact '{artifact}' before it is produced.",
                path=step_path,
                step_id=step.step_id,
            ),
        )
    return tuple(diagnostics)


def _required_phase_diagnostics(
    *,
    enabled_step_types: list[str],
    enabled_ocr_step_count: int,
) -> tuple[OcrPipelineDiagnostic, ...]:
    diagnostics: list[OcrPipelineDiagnostic] = []
    for step_type in _REQUIRED_PHASE1_STEP_TYPES:
        if step_type not in enabled_step_types:
            diagnostics.append(
                error_diagnostic(
                    "REQUIRED_STEP_TYPE_MISSING",
                    f"OCR pipeline requires an enabled '{step_type}' step.",
                    path="steps",
                ),
            )
    if enabled_ocr_step_count > 1:
        diagnostics.append(
            error_diagnostic(
                "MULTIPLE_OCR_STEPS",
                "Phase 1 OCR pipelines support one enabled OCR/parsing step.",
                path="steps",
            ),
        )
    return tuple(diagnostics)
