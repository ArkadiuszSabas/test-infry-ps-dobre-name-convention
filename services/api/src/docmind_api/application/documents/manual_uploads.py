"""Manual browser-upload PDF validation."""

from dataclasses import dataclass
from pathlib import PurePosixPath

from docmind_api.domain.documents.models import normalize_document_original_filename

PDF_CONTENT_TYPE = "application/pdf"
PDF_EXTENSION = ".pdf"
PDF_SIGNATURE = b"%PDF-"


@dataclass(frozen=True, slots=True)
class ManualUploadPdf:
    """Validated PDF accepted from the browser manual upload workflow."""

    original_filename: str
    content_type: str
    content: bytes


def validate_manual_upload_pdf(
    *,
    original_filename: str,
    content_type: str | None,
    content: bytes,
) -> ManualUploadPdf:
    """Validate and normalize browser-uploaded PDF content."""

    safe_filename = normalize_document_original_filename(
        _client_filename_basename(original_filename),
    )
    if PurePosixPath(safe_filename).suffix.lower() != PDF_EXTENSION:
        raise ValueError("Manual upload file must use a .pdf extension.")

    normalized_content_type = (content_type or "").strip().lower()
    if normalized_content_type != PDF_CONTENT_TYPE:
        raise ValueError("Manual upload file content type must be application/pdf.")

    if not content:
        raise ValueError("Document content is required.")
    if not content.startswith(PDF_SIGNATURE):
        raise ValueError("Manual upload file must be a valid PDF document.")

    return ManualUploadPdf(
        original_filename=safe_filename,
        content_type=PDF_CONTENT_TYPE,
        content=content,
    )


def _client_filename_basename(value: str) -> str:
    return value.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
