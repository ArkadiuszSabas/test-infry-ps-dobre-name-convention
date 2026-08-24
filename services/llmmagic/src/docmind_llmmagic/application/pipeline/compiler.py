"""Technical validation and compile use case for OCR pipeline definitions."""

import logging
import re
from collections.abc import Mapping

from docmind_llmmagic.application.pipeline.catalog import ConfigValidator, PipelineBlockCatalog
from docmind_llmmagic.domain.pipeline.catalog import (
    SAFE_PIPELINE_IDENTIFIER_MAX_LENGTH,
    SAFE_PIPELINE_IDENTIFIER_PATTERN,
    PipelineBlockMetadata,
    PipelineBlockStatus,
    PipelineCompileCommand,
    PipelineCompileDiagnostic,
    PipelineCompileResult,
    PipelineDiagnosticSeverity,
    PipelineStepCompileInput,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.models import (
    FailurePolicy,
    PipelineDefinition,
    PipelineStepDefinition,
)

_SAFE_PIPELINE_IDENTIFIER_RE = re.compile(SAFE_PIPELINE_IDENTIFIER_PATTERN)
_LOGGER = logging.getLogger(__name__)


class PipelineDefinitionCompiler:
    """Validate and compile proposed OCR pipeline definitions."""

    def __init__(self, catalog: PipelineBlockCatalog) -> None:
        self.catalog = catalog

    def compile(self, command: PipelineCompileCommand) -> PipelineCompileResult:
        """Return a safe compile result for the proposed definition."""

        diagnostics: list[PipelineCompileDiagnostic] = []
        compiled_steps: list[PipelineStepDefinition] = []
        produced_artifacts: dict[str, str] = {}
        guaranteed_artifacts: dict[str, str] = {}
        seen_step_ids: set[str] = set()

        if not command.pipeline_id:
            diagnostics.append(
                _error(
                    code="PIPELINE_ID_REQUIRED",
                    message="Pipeline id is required.",
                    path="pipeline_id",
                )
            )
        elif not _is_safe_pipeline_identifier(command.pipeline_id):
            diagnostics.append(
                _error(
                    code="PIPELINE_ID_INVALID",
                    message="Pipeline id is invalid.",
                    path="pipeline_id",
                )
            )

        if not command.steps:
            diagnostics.append(
                _error(
                    code="PIPELINE_STEPS_REQUIRED",
                    message="At least one pipeline step is required.",
                    path="steps",
                )
            )

        for index, step in enumerate(command.steps):
            path = f"steps[{index}]"
            block = self.catalog.get(step.implementation_id)

            _validate_step_identity(
                step=step,
                path=path,
                seen_step_ids=seen_step_ids,
                diagnostics=diagnostics,
            )

            if block is None:
                diagnostics.append(
                    _error(
                        code="UNKNOWN_IMPLEMENTATION",
                        message="Pipeline step implementation is not registered.",
                        step_id=_safe_step_id_for_diagnostic(step.step_id),
                        path=f"{path}.implementation_id",
                    )
                )
                continue

            metadata = block.metadata
            effective_config = _effective_config(step=step, metadata=metadata)
            _validate_block_status(step=step, metadata=metadata, path=path, diagnostics=diagnostics)
            _validate_failure_policy(
                step=step,
                metadata=metadata,
                path=path,
                diagnostics=diagnostics,
            )
            _validate_config(
                step=step,
                path=path,
                config=effective_config,
                validate_config=block.validate_config,
                diagnostics=diagnostics,
            )
            _validate_required_artifacts(
                step=step,
                metadata=metadata,
                path=path,
                produced_artifacts=produced_artifacts,
                guaranteed_artifacts=guaranteed_artifacts,
                diagnostics=diagnostics,
            )
            _validate_produced_artifacts(
                step=step,
                metadata=metadata,
                path=path,
                produced_artifacts=produced_artifacts,
                guaranteed_artifacts=guaranteed_artifacts,
                diagnostics=diagnostics,
            )

            compiled_steps.append(
                _compiled_step(step=step, metadata=metadata, config=effective_config)
            )

        has_errors = any(
            diagnostic.severity == PipelineDiagnosticSeverity.ERROR for diagnostic in diagnostics
        )
        compiled_definition = None
        if not has_errors:
            compiled_definition = PipelineDefinition(
                pipeline_id=command.pipeline_id,
                steps=tuple(compiled_steps),
            )

        return PipelineCompileResult(
            valid=not has_errors,
            diagnostics=tuple(diagnostics),
            compiled_definition=compiled_definition,
            catalog_version=self.catalog.version,
            catalog_hash=self.catalog.catalog_hash,
        )


def _validate_step_identity(
    *,
    step: PipelineStepCompileInput,
    path: str,
    seen_step_ids: set[str],
    diagnostics: list[PipelineCompileDiagnostic],
) -> None:
    if not step.step_id:
        diagnostics.append(
            _error(
                code="STEP_ID_REQUIRED",
                message="Pipeline step id is required.",
                path=f"{path}.step_id",
            )
        )
        return

    if not _is_safe_pipeline_identifier(step.step_id):
        diagnostics.append(
            _error(
                code="STEP_ID_INVALID",
                message="Pipeline step id is invalid.",
                path=f"{path}.step_id",
            )
        )
        return

    if step.step_id in seen_step_ids:
        diagnostics.append(
            _error(
                code="DUPLICATE_STEP_ID",
                message="Pipeline step ids must be unique.",
                step_id=_safe_step_id_for_diagnostic(step.step_id),
                path=f"{path}.step_id",
            )
        )
        return

    seen_step_ids.add(step.step_id)


def _validate_block_status(
    *,
    step: PipelineStepCompileInput,
    metadata: PipelineBlockMetadata,
    path: str,
    diagnostics: list[PipelineCompileDiagnostic],
) -> None:
    if not step.enabled:
        return

    if metadata.status in {PipelineBlockStatus.DISABLED, PipelineBlockStatus.PLANNED}:
        diagnostics.append(
            _error(
                code="BLOCK_NOT_AVAILABLE",
                message="Pipeline block is not available for enabled definitions.",
                step_id=_safe_step_id_for_diagnostic(step.step_id),
                path=f"{path}.implementation_id",
            )
        )
        return

    if metadata.status == PipelineBlockStatus.DEPRECATED:
        diagnostics.append(
            PipelineCompileDiagnostic(
                severity=PipelineDiagnosticSeverity.WARNING,
                code="BLOCK_DEPRECATED",
                message="Pipeline block is deprecated.",
                step_id=_safe_step_id_for_diagnostic(step.step_id),
                path=f"{path}.implementation_id",
            )
        )


def _validate_failure_policy(
    *,
    step: PipelineStepCompileInput,
    metadata: PipelineBlockMetadata,
    path: str,
    diagnostics: list[PipelineCompileDiagnostic],
) -> None:
    if step.failure_policy in metadata.allowed_failure_policies:
        return

    diagnostics.append(
        _error(
            code="FAILURE_POLICY_NOT_ALLOWED",
            message="Failure policy is not allowed for this pipeline block.",
            step_id=_safe_step_id_for_diagnostic(step.step_id),
            path=f"{path}.failure_policy",
        )
    )


def _validate_config(
    *,
    step: PipelineStepCompileInput,
    path: str,
    config: Mapping[str, object],
    validate_config: ConfigValidator,
    diagnostics: list[PipelineCompileDiagnostic],
) -> None:
    try:
        validate_config(config)
    except PipelineStepError as exc:
        diagnostics.append(
            _error(
                code=exc.code,
                message=exc.message,
                step_id=_safe_step_id_for_diagnostic(step.step_id),
                path=f"{path}.config",
            )
        )
    except Exception:
        _LOGGER.exception(
            "Unexpected pipeline step configuration validation failure.",
            extra={"pipeline_step_id": _safe_step_id_for_diagnostic(step.step_id)},
        )
        diagnostics.append(
            _error(
                code="CONFIG_INVALID",
                message="Pipeline step configuration is invalid.",
                step_id=_safe_step_id_for_diagnostic(step.step_id),
                path=f"{path}.config",
            )
        )


def _validate_required_artifacts(
    *,
    step: PipelineStepCompileInput,
    metadata: PipelineBlockMetadata,
    path: str,
    produced_artifacts: dict[str, str],
    guaranteed_artifacts: dict[str, str],
    diagnostics: list[PipelineCompileDiagnostic],
) -> None:
    if not step.enabled:
        return

    for artifact_key in metadata.requires:
        if artifact_key not in produced_artifacts:
            diagnostics.append(
                _error(
                    code="MISSING_REQUIRED_ARTIFACT",
                    message="Pipeline step requires an artifact that is not produced earlier.",
                    step_id=_safe_step_id_for_diagnostic(step.step_id),
                    path=f"{path}.implementation_id",
                )
            )
            continue

        if (
            step.failure_policy == FailurePolicy.REQUIRED
            and artifact_key not in guaranteed_artifacts
        ):
            diagnostics.append(
                _error(
                    code="REQUIRED_ARTIFACT_NOT_GUARANTEED",
                    message=(
                        "Required step depends on an artifact produced only by an optional step."
                    ),
                    step_id=_safe_step_id_for_diagnostic(step.step_id),
                    path=f"{path}.implementation_id",
                )
            )


def _validate_produced_artifacts(
    *,
    step: PipelineStepCompileInput,
    metadata: PipelineBlockMetadata,
    path: str,
    produced_artifacts: dict[str, str],
    guaranteed_artifacts: dict[str, str],
    diagnostics: list[PipelineCompileDiagnostic],
) -> None:
    if not step.enabled:
        return

    for artifact_key in metadata.produces:
        existing_step_id = produced_artifacts.get(artifact_key)
        if existing_step_id is not None:
            diagnostics.append(
                _error(
                    code="DUPLICATE_ARTIFACT_PRODUCER",
                    message="Pipeline artifact is produced by more than one enabled step.",
                    step_id=_safe_step_id_for_diagnostic(step.step_id),
                    path=f"{path}.implementation_id",
                )
            )
            continue

        produced_artifacts[artifact_key] = step.step_id
        if step.failure_policy == FailurePolicy.REQUIRED:
            guaranteed_artifacts[artifact_key] = step.step_id


def _effective_config(
    *,
    step: PipelineStepCompileInput,
    metadata: PipelineBlockMetadata,
) -> dict[str, object]:
    return {**metadata.default_config, **step.config}


def _compiled_step(
    *,
    step: PipelineStepCompileInput,
    metadata: PipelineBlockMetadata,
    config: Mapping[str, object],
) -> PipelineStepDefinition:
    return PipelineStepDefinition(
        step_id=step.step_id,
        step_type=metadata.step_type,
        implementation_id=metadata.implementation_id,
        display_name=metadata.display_name,
        config=dict(config),
        failure_policy=step.failure_policy,
        enabled=step.enabled,
    )


def _is_safe_pipeline_identifier(value: str) -> bool:
    return (
        len(value) <= SAFE_PIPELINE_IDENTIFIER_MAX_LENGTH
        and _SAFE_PIPELINE_IDENTIFIER_RE.fullmatch(value) is not None
    )


def _safe_step_id_for_diagnostic(step_id: str) -> str | None:
    if _is_safe_pipeline_identifier(step_id):
        return step_id
    return None


def _error(
    *,
    code: str,
    message: str,
    step_id: str | None = None,
    path: str | None = None,
) -> PipelineCompileDiagnostic:
    return PipelineCompileDiagnostic(
        severity=PipelineDiagnosticSeverity.ERROR,
        code=code,
        message=message,
        step_id=step_id,
        path=path,
    )
