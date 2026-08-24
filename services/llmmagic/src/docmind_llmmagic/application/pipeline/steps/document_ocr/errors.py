"""Safe OCR/parsing error helpers."""

import re

from docmind_llmmagic.domain.pipeline.errors import PipelineStepError

_SAFE_ERROR_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")


class DocumentOcrPageError(Exception):
    """Page-level OCR/parsing failure with a safe public error code."""

    def __init__(self, error_code: str) -> None:
        if _SAFE_ERROR_CODE_PATTERN.fullmatch(error_code) is None:
            error_code = "OCR_PAGE_FAILED"
        super().__init__(error_code)
        self.error_code = error_code


def safe_ocr_error(*, code: str, message: str) -> PipelineStepError:
    """Return a sanitized pipeline step error for document OCR/parsing."""

    return PipelineStepError(code=code, message=message)


def safe_ocr_page_error(error_code: str) -> DocumentOcrPageError:
    """Return a sanitized page-level OCR/parsing error."""

    return DocumentOcrPageError(error_code)
