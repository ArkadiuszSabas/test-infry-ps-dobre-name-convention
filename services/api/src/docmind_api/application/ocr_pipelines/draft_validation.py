"""Draft-write validation for OCR pipeline definitions."""

from docmind_api.application.ocr_pipelines.config_schema import config_schema_diagnostics
from docmind_api.application.ocr_pipelines.diagnostics import error_diagnostic
from docmind_api.application.ocr_pipelines.secret_config import secret_config_diagnostics
from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineBlockCatalog,
    OcrPipelineDiagnostic,
    OcrPipelineDraftDefinition,
)


def draft_write_diagnostics(
    *,
    definition: OcrPipelineDraftDefinition,
    catalog: OcrPipelineBlockCatalog,
) -> tuple[OcrPipelineDiagnostic, ...]:
    """Return diagnostics that must block storing a draft payload."""

    diagnostics: list[OcrPipelineDiagnostic] = []
    blocks = catalog.by_implementation_id()
    for index, step in enumerate(definition.steps):
        diagnostics.extend(secret_config_diagnostics(step=step, step_index=index))
        block = blocks.get(step.implementation_id)
        if block is None:
            diagnostics.append(
                error_diagnostic(
                    "UNKNOWN_PIPELINE_BLOCK",
                    "OCR pipeline step references an unknown block implementation.",
                    path=f"steps[{index}].implementation_id",
                    step_id=step.step_id,
                ),
            )
            continue
        diagnostics.extend(config_schema_diagnostics(block=block, step=step, step_index=index))
    return tuple(diagnostics)
