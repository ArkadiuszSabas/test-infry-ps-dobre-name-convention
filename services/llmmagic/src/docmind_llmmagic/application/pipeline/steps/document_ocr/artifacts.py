"""OCR/parsing artifact mapping helpers."""

from docmind_llmmagic.domain.pipeline.models import MetricValue
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrDocumentArtifact,
    OcrFallbackStatus,
    OcrPageArtifact,
    OcrPageStatus,
    OcrParsingConfig,
    OcrProviderPageResult,
    OcrQualitySummary,
)
from docmind_llmmagic.domain.pipeline.preprocessing import PreprocessedPageArtifact


def parsed_page(
    *,
    source_page: PreprocessedPageArtifact,
    provider_result: OcrProviderPageResult,
    config: OcrParsingConfig,
) -> OcrPageArtifact:
    """Map a provider page result to the internal OCR artifact contract."""

    words = provider_result.words if config.include_word_details else ()
    return OcrPageArtifact(
        page_number=source_page.page_number,
        status=OcrPageStatus.PARSED,
        source_storage_reference=source_page.storage_reference,
        text=provider_result.text,
        lines=provider_result.lines,
        words=words,
        width_px=provider_result.width_px or source_page.width_px,
        height_px=provider_result.height_px or source_page.height_px,
        format=provider_result.format or source_page.format,
        dpi=provider_result.dpi if provider_result.dpi is not None else source_page.dpi,
        provider_id=config.provider_id,
        model_id=config.model_id,
        confidence=provider_result.confidence,
        key_value_pairs=provider_result.key_value_pairs,
        selection_marks=provider_result.selection_marks,
        warning_codes=provider_result.warning_codes,
        provider_page_count=provider_result.provider_page_count,
        coordinate_width=provider_result.coordinate_width
        or _coordinate_dimension(source_page.width_px),
        coordinate_height=provider_result.coordinate_height
        or _coordinate_dimension(source_page.height_px),
    )


def _coordinate_dimension(value: int | None) -> float | None:
    return float(value) if value is not None and value > 0 else None


def quality_summary(
    *,
    pages: list[OcrPageArtifact],
    config: OcrParsingConfig,
) -> OcrQualitySummary:
    """Build safe aggregate OCR quality metrics."""

    confidence_values = [
        page.confidence
        for page in pages
        if page.status == OcrPageStatus.PARSED and page.confidence is not None
    ]
    average_confidence = (
        round(sum(confidence_values) / len(confidence_values), 6) if confidence_values else None
    )
    low_confidence_page_count = sum(
        page.status == OcrPageStatus.PARSED
        and page.confidence is not None
        and page.confidence < config.low_confidence_threshold
        for page in pages
    )
    warning_count = sum(len(page.warning_codes) for page in pages)
    return OcrQualitySummary(
        average_confidence=average_confidence,
        low_confidence_page_count=low_confidence_page_count,
        warning_count=warning_count,
    )


def step_metrics(
    *,
    document_artifact: OcrDocumentArtifact,
    quality: OcrQualitySummary,
) -> dict[str, MetricValue]:
    """Build safe OCR step trace metrics."""

    metrics: dict[str, MetricValue] = {
        "page_count": document_artifact.total_page_count,
        "succeeded_page_count": document_artifact.succeeded_page_count,
        "failed_page_count": document_artifact.failed_page_count,
        "partial_page_failure": document_artifact.failed_page_count > 0,
        "low_confidence_page_count": quality.low_confidence_page_count,
        "warning_count": quality.warning_count,
        "key_value_pair_count": len(document_artifact.key_value_pairs),
        "table_count": len(document_artifact.tables),
        "selection_mark_count": sum(len(page.selection_marks) for page in document_artifact.pages),
    }
    if quality.average_confidence is not None:
        metrics["average_confidence"] = quality.average_confidence
    if document_artifact.fallback_status != OcrFallbackStatus.NOT_CONFIGURED:
        metrics.update(
            {
                "fallback_configured": True,
                "fallback_started": document_artifact.fallback_status
                not in (OcrFallbackStatus.SKIPPED, OcrFallbackStatus.NOT_CONFIGURED),
                "fallback_skipped": document_artifact.fallback_status == OcrFallbackStatus.SKIPPED,
                "fallback_succeeded": document_artifact.fallback_status
                == OcrFallbackStatus.SUCCEEDED,
                "fallback_warning": document_artifact.fallback_status == OcrFallbackStatus.WARNING,
                "fallback_failed": document_artifact.fallback_status == OcrFallbackStatus.FAILED,
                "fallback_triggered_page_count": document_artifact.fallback_triggered_page_count,
                "fallback_succeeded_page_count": document_artifact.fallback_succeeded_page_count,
                "fallback_failed_page_count": document_artifact.fallback_failed_page_count,
                "fallback_skipped_page_count": document_artifact.fallback_skipped_page_count,
            }
        )

    return metrics


def page_metadata(page: OcrPageArtifact) -> dict[str, MetricValue]:
    """Build safe page artifact metadata."""

    metadata: dict[str, MetricValue] = {
        "page_number": page.page_number,
        "parsed": page.status == OcrPageStatus.PARSED,
        "failed": page.status == OcrPageStatus.FAILED,
        "line_count": len(page.lines),
        "word_count": len(page.words),
        "selection_mark_count": len(page.selection_marks),
        "warning_count": len(page.warning_codes),
        "fallback_triggered": bool(page.fallback_reason_codes),
        "fallback_used": page.fallback_used,
        "fallback_failed": page.fallback_error_code is not None and not page.fallback_used,
    }
    if page.width_px is not None:
        metadata["width_px"] = page.width_px
    if page.height_px is not None:
        metadata["height_px"] = page.height_px
    if page.dpi is not None:
        metadata["dpi"] = page.dpi
    if page.confidence is not None:
        metadata["confidence"] = page.confidence
    if page.provider_page_count:
        metadata["provider_page_count"] = page.provider_page_count

    return metadata
