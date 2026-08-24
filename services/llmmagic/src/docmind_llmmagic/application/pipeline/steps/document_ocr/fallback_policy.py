"""Fallback OCR/Vision trigger and limit policy helpers."""

from docmind_llmmagic.domain.pipeline.ocr import OcrPageArtifact, OcrParsingConfig
from docmind_llmmagic.domain.pipeline.preflight import DocumentInputKind

FALLBACK_REASON_LOW_CONFIDENCE = "OCR_FALLBACK_REASON_LOW_CONFIDENCE"
FALLBACK_REASON_PROVIDER_ERROR = "OCR_FALLBACK_REASON_PROVIDER_ERROR"
FALLBACK_REASON_PAGE_FAILURE = "OCR_FALLBACK_REASON_PAGE_FAILURE"
FALLBACK_REASON_EMPTY_TEXT = "OCR_FALLBACK_REASON_EMPTY_TEXT"
FALLBACK_REASON_LOW_TEXT_LENGTH = "OCR_FALLBACK_REASON_LOW_TEXT_LENGTH"
FALLBACK_REASON_LOW_LINE_COUNT = "OCR_FALLBACK_REASON_LOW_LINE_COUNT"

FALLBACK_PROVIDER_UNAVAILABLE = "OCR_FALLBACK_PROVIDER_UNAVAILABLE"
FALLBACK_DOCUMENT_KIND_BLOCKED = "OCR_FALLBACK_DOCUMENT_KIND_BLOCKED"
FALLBACK_PAGE_LIMIT_EXCEEDED = "OCR_FALLBACK_PAGE_LIMIT_EXCEEDED"
FALLBACK_COST_LIMIT_EXCEEDED = "OCR_FALLBACK_COST_LIMIT_EXCEEDED"
FALLBACK_PROCESSING_TIMEOUT = "OCR_FALLBACK_PROCESSING_TIMEOUT"
FALLBACK_FAILED = "OCR_FALLBACK_FAILED"


def fallback_reasons_for_provider_error(
    *,
    error_code: str,
    config: OcrParsingConfig,
) -> tuple[str, ...]:
    """Return explicit fallback trigger reasons for a primary provider/page failure."""

    reason_codes: list[str] = []
    if config.fallback.trigger_on_provider_error and (
        error_code.startswith("OCR_PROVIDER_") or error_code == "OCR_PAGE_FAILED"
    ):
        reason_codes.append(FALLBACK_REASON_PROVIDER_ERROR)
    if config.fallback.trigger_on_page_failure:
        reason_codes.append(FALLBACK_REASON_PAGE_FAILURE)

    return tuple(reason_codes)


def fallback_reasons_for_result(
    *,
    page: OcrPageArtifact,
    config: OcrParsingConfig,
) -> tuple[str, ...]:
    """Return explicit fallback trigger reasons for a parsed primary OCR page."""

    fallback = config.fallback
    reason_codes: list[str] = []
    if (
        fallback.trigger_on_low_confidence
        and page.confidence is not None
        and page.confidence < config.low_confidence_threshold
    ):
        reason_codes.append(FALLBACK_REASON_LOW_CONFIDENCE)
    if fallback.trigger_on_empty_text and not page.text.strip():
        reason_codes.append(FALLBACK_REASON_EMPTY_TEXT)
    if fallback.min_text_length is not None and len(page.text.strip()) < fallback.min_text_length:
        reason_codes.append(FALLBACK_REASON_LOW_TEXT_LENGTH)
    if fallback.min_line_count is not None and len(page.lines) < fallback.min_line_count:
        reason_codes.append(FALLBACK_REASON_LOW_LINE_COUNT)

    return tuple(reason_codes)


def fallback_skip_reason(
    *,
    config: OcrParsingConfig,
    document_kind: DocumentInputKind | None,
    fallback_provider_available: bool,
    attempted_page_count: int,
) -> str | None:
    """Return a safe reason code when a triggered fallback must be skipped."""

    fallback = config.fallback
    if not fallback_provider_available:
        return FALLBACK_PROVIDER_UNAVAILABLE
    if fallback.allowed_document_kinds and document_kind not in fallback.allowed_document_kinds:
        return FALLBACK_DOCUMENT_KIND_BLOCKED
    if attempted_page_count >= fallback.max_pages:
        return FALLBACK_PAGE_LIMIT_EXCEEDED
    if _estimated_cost_units(attempted_page_count + 1) > fallback.max_estimated_cost_units:
        return FALLBACK_COST_LIMIT_EXCEEDED

    return None


def _estimated_cost_units(page_count: int) -> int:
    return page_count
