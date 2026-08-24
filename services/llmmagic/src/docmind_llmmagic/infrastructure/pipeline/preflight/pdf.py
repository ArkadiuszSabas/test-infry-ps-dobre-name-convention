"""Bounded structural PDF inspection for document preflight."""

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Protocol, cast

from docmind_llmmagic.application.pipeline.steps.document_preflight.errors import (
    safe_preflight_error,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError

_PDF_HEADER = b"%PDF-"
_PDF_EOF_MARKER = b"%%EOF"
_PDF_HEADER_SCAN_BYTES = 1024
_PDF_EOF_SCAN_BYTES = 8192


class _PdfiumPage(Protocol):
    def get_size(self) -> tuple[float, float]: ...

    def close(self) -> None: ...


class _PdfiumDocument(Protocol):
    def __len__(self) -> int: ...

    def __getitem__(self, index: int) -> _PdfiumPage: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class PdfInspection:
    """Safe structural metadata resolved from a complete PDF payload."""

    page_count: int


class PdfiumPdfInspector:
    """Validate PDF structure and every page tree entry without rendering pages."""

    def __init__(
        self,
        *,
        open_pdf: Callable[[bytes], _PdfiumDocument] | None = None,
    ) -> None:
        self._open_pdf = open_pdf or cast(
            Callable[[bytes], _PdfiumDocument],
            import_module("pypdfium2").PdfDocument,
        )

    def inspect(self, content: bytes) -> PdfInspection:
        """Return page metadata after validating the complete PDF structure."""

        if (
            _PDF_HEADER not in content[:_PDF_HEADER_SCAN_BYTES]
            or _PDF_EOF_MARKER not in content[-_PDF_EOF_SCAN_BYTES:]
        ):
            raise _invalid_pdf()

        document: _PdfiumDocument | None = None
        try:
            document = self._open_pdf(content)
            page_count = len(document)
            if page_count < 1:
                raise safe_preflight_error(
                    code="PREFLIGHT_PDF_EMPTY",
                    message="Document preflight requires at least one PDF page.",
                )
            for page_index in range(page_count):
                page = document[page_index]
                try:
                    width_points, height_points = page.get_size()
                    if width_points <= 0 or height_points <= 0:
                        raise _invalid_pdf()
                finally:
                    page.close()
            return PdfInspection(page_count=page_count)
        except PipelineStepError:
            raise
        except Exception as exc:
            raise _invalid_pdf() from exc
        finally:
            if document is not None:
                document.close()


def _invalid_pdf() -> PipelineStepError:
    return safe_preflight_error(
        code="PREFLIGHT_PDF_INVALID",
        message="Document preflight source is not a valid PDF.",
    )
