"""Safe OCR result projection for pipeline invocation responses."""

from dataclasses import dataclass

from docmind_llmmagic.application.pipeline.steps.document_ocr.constants import (
    OCR_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.domain.pipeline.models import PipelineContext
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrDocumentArtifact,
    OcrKeyValuePair,
    OcrPageArtifact,
)

MAX_RESULT_PAGE_COUNT = 50
MAX_RESULT_TEXT_LENGTH = 200_000
MAX_PAGE_TEXT_LENGTH = 20_000
MAX_PAGE_LINE_COUNT = 250
MAX_LINE_TEXT_LENGTH = 1_000
MAX_KEY_VALUE_PAIR_COUNT = 2_000
MAX_KEY_VALUE_TEXT_LENGTH = 1_000


@dataclass(frozen=True, slots=True)
class PipelineInvocationOcrPageResult:
    """Safe user-facing OCR result for one page."""

    page_number: int
    status: str
    text: str
    text_truncated: bool
    lines: tuple[str, ...]
    lines_truncated: bool
    confidence: float | None
    warning_codes: tuple[str, ...]
    error_code: str | None
    fallback_used: bool
    fallback_reason_codes: tuple[str, ...]
    primary_error_code: str | None


@dataclass(frozen=True, slots=True)
class PipelineInvocationOcrKeyValuePair:
    """Safe user-facing OCR key-value pair detected by the provider."""

    key: str
    value: str
    key_truncated: bool
    value_truncated: bool
    confidence: float | None
    page_number: int
    bounding_polygon: tuple[float, ...]
    order_index: int
    source: str


@dataclass(frozen=True, slots=True)
class PipelineInvocationOcrResult:
    """Safe user-facing OCR result extracted from pipeline artifacts."""

    status: str
    provider_id: str
    model_id: str
    total_page_count: int
    succeeded_page_count: int
    failed_page_count: int
    average_confidence: float | None
    low_confidence_page_count: int
    warning_count: int
    pages_truncated: bool
    pages: tuple[PipelineInvocationOcrPageResult, ...]
    key_value_pairs_truncated: bool
    key_value_pairs: tuple[PipelineInvocationOcrKeyValuePair, ...]


def ocr_result_from_context(context: PipelineContext) -> PipelineInvocationOcrResult | None:
    """Return a bounded safe OCR display result from the final pipeline context."""

    artifact = context.artifacts.get(OCR_RESULT_ARTIFACT_KEY)
    if artifact is None or not isinstance(artifact.value, OcrDocumentArtifact):
        return None

    result = artifact.value
    pages, pages_truncated = _page_results(result.pages)
    key_value_pairs, key_value_pairs_truncated = _key_value_pair_results(result.key_value_pairs)
    return PipelineInvocationOcrResult(
        status=result.status.value,
        provider_id=result.provider_id.value,
        model_id=result.model_id,
        total_page_count=result.total_page_count,
        succeeded_page_count=result.succeeded_page_count,
        failed_page_count=result.failed_page_count,
        average_confidence=result.quality.average_confidence,
        low_confidence_page_count=result.quality.low_confidence_page_count,
        warning_count=result.quality.warning_count,
        pages_truncated=pages_truncated,
        pages=pages,
        key_value_pairs_truncated=key_value_pairs_truncated,
        key_value_pairs=key_value_pairs,
    )


def _page_results(
    pages: tuple[OcrPageArtifact, ...],
) -> tuple[tuple[PipelineInvocationOcrPageResult, ...], bool]:
    selected_pages: list[PipelineInvocationOcrPageResult] = []
    remaining_text_length = MAX_RESULT_TEXT_LENGTH

    for page in pages:
        if len(selected_pages) >= MAX_RESULT_PAGE_COUNT or remaining_text_length <= 0:
            return tuple(selected_pages), True

        page_result = _page_result(page, remaining_text_length)
        selected_pages.append(page_result)
        remaining_text_length -= _page_text_length(page_result)

    return tuple(selected_pages), False


def _page_result(
    page: OcrPageArtifact,
    remaining_text_length: int,
) -> PipelineInvocationOcrPageResult:
    text_limit = min(MAX_PAGE_TEXT_LENGTH, max(remaining_text_length, 0))
    text, text_truncated = _truncate(page.text, text_limit)
    lines, lines_truncated = _line_results(page, remaining_text_length - len(text))
    return PipelineInvocationOcrPageResult(
        page_number=page.page_number,
        status=page.status.value,
        text=text,
        text_truncated=text_truncated,
        lines=lines,
        lines_truncated=lines_truncated,
        confidence=page.confidence,
        warning_codes=page.warning_codes,
        error_code=page.error_code,
        fallback_used=page.fallback_used,
        fallback_reason_codes=page.fallback_reason_codes,
        primary_error_code=page.primary_error_code,
    )


def _line_results(
    page: OcrPageArtifact, remaining_text_length: int
) -> tuple[tuple[str, ...], bool]:
    if remaining_text_length <= 0:
        return (), bool(page.lines)

    values: list[str] = []
    lines_truncated = False
    for line in page.lines[:MAX_PAGE_LINE_COUNT]:
        if remaining_text_length <= 0:
            lines_truncated = True
            break
        line_limit = min(MAX_LINE_TEXT_LENGTH, remaining_text_length)
        value, value_truncated = _truncate(line.content, line_limit)
        values.append(value)
        remaining_text_length -= len(value)
        lines_truncated = lines_truncated or value_truncated

    lines_truncated = lines_truncated or len(page.lines) > len(values)
    return tuple(values), lines_truncated


def _page_text_length(page: PipelineInvocationOcrPageResult) -> int:
    return len(page.text) + sum(len(line) for line in page.lines)


def _key_value_pair_results(
    key_value_pairs: tuple[OcrKeyValuePair, ...],
) -> tuple[tuple[PipelineInvocationOcrKeyValuePair, ...], bool]:
    values: list[PipelineInvocationOcrKeyValuePair] = []
    for pair in key_value_pairs[:MAX_KEY_VALUE_PAIR_COUNT]:
        key, key_truncated = _truncate(pair.key, MAX_KEY_VALUE_TEXT_LENGTH)
        value, value_truncated = _truncate(pair.value, MAX_KEY_VALUE_TEXT_LENGTH)
        values.append(
            PipelineInvocationOcrKeyValuePair(
                key=key,
                value=value,
                key_truncated=key_truncated,
                value_truncated=value_truncated,
                confidence=pair.confidence,
                page_number=pair.page_number,
                bounding_polygon=pair.bounding_polygon,
                order_index=pair.order_index,
                source=pair.source,
            )
        )

    return tuple(values), len(key_value_pairs) > len(values)


def _truncate(value: str, max_length: int) -> tuple[str, bool]:
    if max_length <= 0:
        return "", bool(value)
    if len(value) <= max_length:
        return value, False
    return value[:max_length], True
