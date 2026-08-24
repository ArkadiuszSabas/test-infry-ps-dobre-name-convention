"""Diagnostic builders for OCR pipeline validation."""

from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineDiagnostic,
    OcrPipelineDiagnosticSeverity,
)


def error_diagnostic(
    code: str,
    message: str,
    *,
    path: str | None = None,
    step_id: str | None = None,
) -> OcrPipelineDiagnostic:
    """Build a blocking validation diagnostic."""

    return OcrPipelineDiagnostic(
        severity=OcrPipelineDiagnosticSeverity.ERROR,
        code=code,
        path=path,
        step_id=step_id,
        message=message,
    )
