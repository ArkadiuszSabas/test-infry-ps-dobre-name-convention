"""Safe structural summaries for pipeline step input and output logging."""

from collections.abc import Mapping
from typing import cast

from docmind_llmmagic.domain.pipeline.models import PipelineArtifact
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrBoundingRegion,
    OcrDocumentArtifact,
    OcrKeyValuePair,
    OcrPageArtifact,
    OcrSelectionMark,
    OcrTable,
    OcrTableCell,
    OcrTextSpan,
)

_MAX_LOGGED_ARTIFACTS = 32
_MAX_INFO_ARTIFACTS = 16
_MAX_LOGGED_OCR_PAGES = 50
_MAX_LOGGED_OCR_TABLES = 50
_MAX_LOGGED_FIELD_NAMES = 64


def summarize_artifacts(
    artifacts: Mapping[str, PipelineArtifact],
    *,
    detailed: bool = False,
) -> dict[str, object]:
    """Return bounded structural artifact summaries without document-derived content."""

    ordered = sorted(artifacts.items())
    limit = _MAX_LOGGED_ARTIFACTS if detailed else _MAX_INFO_ARTIFACTS
    selected = ordered[:limit]
    return {
        "artifact_count": len(ordered),
        "artifacts_truncated": len(ordered) > len(selected),
        "artifacts": [
            _artifact_summary(key, artifact, detailed=detailed) for key, artifact in selected
        ],
    }


def changed_artifacts(
    before: Mapping[str, PipelineArtifact],
    after: Mapping[str, PipelineArtifact],
) -> dict[str, PipelineArtifact]:
    """Return artifacts added or replaced by one pipeline step."""

    return {key: artifact for key, artifact in after.items() if before.get(key) is not artifact}


def _artifact_summary(
    key: str,
    artifact: PipelineArtifact,
    *,
    detailed: bool,
) -> dict[str, object]:
    value = artifact.value
    summary: dict[str, object] = {
        "artifact_key": key,
        "artifact_type": type(value).__name__,
        "produced_by_step_id": artifact.produced_by_step_id,
    }
    if detailed:
        summary["artifact_fields"] = _field_names(type(value))
        summary["metadata"] = dict(artifact.metadata)
    if isinstance(value, OcrDocumentArtifact):
        summary["ocr_result"] = _ocr_document_summary(value, detailed=detailed)
    return summary


def _ocr_document_summary(
    artifact: OcrDocumentArtifact,
    *,
    detailed: bool,
) -> dict[str, object]:
    pages = artifact.pages[:_MAX_LOGGED_OCR_PAGES]
    tables = artifact.tables[:_MAX_LOGGED_OCR_TABLES]
    summary: dict[str, object] = {
        "status": artifact.status.value,
        "provider_id": artifact.provider_id.value,
        "model_id": artifact.model_id,
        "total_page_count": artifact.total_page_count,
        "succeeded_page_count": artifact.succeeded_page_count,
        "failed_page_count": artifact.failed_page_count,
        "average_confidence": artifact.quality.average_confidence,
        "low_confidence_page_count": artifact.quality.low_confidence_page_count,
        "warning_count": artifact.quality.warning_count,
        "key_value_pair_count": len(artifact.key_value_pairs),
        "table_count": len(artifact.tables),
        "table_cell_count": sum(len(table.cells) for table in artifact.tables),
        "selection_mark_count": sum(len(page.selection_marks) for page in artifact.pages),
        "result_shape": {
            "document_fields": _field_names(OcrDocumentArtifact),
            "page_fields": _field_names(OcrPageArtifact),
            "key_value_pair_fields": _field_names(OcrKeyValuePair),
            "table_fields": _field_names(OcrTable),
            "table_cell_fields": _field_names(OcrTableCell),
            "selection_mark_fields": _field_names(OcrSelectionMark),
            "bounding_region_fields": _field_names(OcrBoundingRegion),
            "text_span_fields": _field_names(OcrTextSpan),
        },
    }
    if detailed:
        summary.update(
            {
                "pages_truncated": len(artifact.pages) > len(pages),
                "pages": [_ocr_page_summary(page) for page in pages],
                "tables_truncated": len(artifact.tables) > len(tables),
                "tables": [_ocr_table_summary(table) for table in tables],
            }
        )
    return summary


def _ocr_page_summary(page: OcrPageArtifact) -> dict[str, object]:
    selected_count = sum(mark.state.value == "selected" for mark in page.selection_marks)
    return {
        "page_number": page.page_number,
        "status": page.status.value,
        "line_count": len(page.lines),
        "word_count": len(page.words),
        "key_value_pair_count": len(page.key_value_pairs),
        "selection_mark_count": len(page.selection_marks),
        "selected_mark_count": selected_count,
        "unselected_mark_count": len(page.selection_marks) - selected_count,
        "confidence": page.confidence,
        "warning_count": len(page.warning_codes),
        "fallback_used": page.fallback_used,
    }


def _ocr_table_summary(table: OcrTable) -> dict[str, object]:
    return {
        "table_id": table.table_id,
        "row_count": table.row_count,
        "column_count": table.column_count,
        "cell_count": len(table.cells),
        "span_count": len(table.spans),
        "page_numbers": sorted(
            {region.page_number for region in table.bounding_regions}
            | {region.page_number for cell in table.cells for region in cell.bounding_regions}
        ),
    }


def _field_names(model_type: type[object]) -> list[str]:
    raw_fields = getattr(model_type, "__dataclass_fields__", None)
    if not isinstance(raw_fields, Mapping):
        return []
    field_mapping = cast(Mapping[object, object], raw_fields)
    return [str(name) for name in field_mapping][:_MAX_LOGGED_FIELD_NAMES]
