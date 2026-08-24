"""Map Azure Document Intelligence layout structures into safe OCR contracts."""

from collections.abc import Sequence
from typing import cast

from docmind_llmmagic.domain.pipeline.ocr import (
    OcrBoundingRegion,
    OcrSelectionMark,
    OcrSelectionMarkState,
    OcrTable,
    OcrTableCell,
    OcrTextLine,
    OcrTextSpan,
)


def document_page_text(
    *,
    result: object,
    page: object | None,
    lines: tuple[OcrTextLine, ...],
    page_count: int,
) -> str:
    """Return text owned by one page without leaking document content into page one."""

    if lines:
        return "\n".join(line.content for line in lines)

    content = getattr(result, "content", None)
    if not isinstance(content, str):
        return ""
    spans = _object_sequence(getattr(page, "spans", ()))
    page_content: list[str] = []
    for span in spans:
        offset = getattr(span, "offset", None)
        length = getattr(span, "length", None)
        if (
            isinstance(offset, int)
            and not isinstance(offset, bool)
            and isinstance(length, int)
            and not isinstance(length, bool)
            and offset >= 0
            and length > 0
            and offset < len(content)
        ):
            page_content.append(content[offset : min(len(content), offset + length)])
    if page_content:
        return "".join(page_content)
    return content if page_count == 1 else ""


def map_selection_marks(
    page: object | None,
    *,
    page_number: int,
) -> tuple[OcrSelectionMark, ...]:
    """Map page-level checkboxes and other selection marks."""

    if page is None:
        return ()

    values: list[OcrSelectionMark] = []
    raw_marks = _object_sequence(getattr(page, "selection_marks", ()))
    for source_index, mark in enumerate(raw_marks, start=1):
        state = _selection_mark_state(getattr(mark, "state", None))
        polygon = _polygon(getattr(mark, "polygon", ()))
        if state is None:
            continue

        values.append(
            OcrSelectionMark(
                state=state,
                confidence=_confidence(getattr(mark, "confidence", None)),
                bounding_region=OcrBoundingRegion(
                    page_number=page_number,
                    bounding_polygon=polygon,
                ),
                span=_span(getattr(mark, "span", None)),
                order_index=source_index,
            )
        )

    return tuple(values)


def map_tables(
    result: object,
    *,
    table_id_prefix: str,
    page_number_override: int | None = None,
) -> tuple[OcrTable, ...]:
    """Map document or page tables with structured cells and provenance."""

    values: list[OcrTable] = []
    raw_tables = _object_sequence(getattr(result, "tables", ()))
    for source_index, table in enumerate(raw_tables, start=1):
        row_count = _positive_int(getattr(table, "row_count", None))
        column_count = _positive_int(getattr(table, "column_count", None))
        if row_count is None or column_count is None:
            continue

        values.append(
            OcrTable(
                table_id=f"{table_id_prefix}-table-{source_index}",
                row_count=row_count,
                column_count=column_count,
                cells=_table_cells(table, page_number_override=page_number_override),
                order_index=source_index,
                spans=_spans(getattr(table, "spans", ())),
                span_page_number=page_number_override,
                bounding_regions=_bounding_regions(
                    getattr(table, "bounding_regions", ()),
                    page_number_override=page_number_override,
                ),
            )
        )

    return tuple(values)


def _selection_mark_state(value: object) -> OcrSelectionMarkState | None:
    if not isinstance(value, str):
        return None
    try:
        return OcrSelectionMarkState(value.lower())
    except ValueError:
        return None


def _table_cells(
    table: object,
    *,
    page_number_override: int | None,
) -> tuple[OcrTableCell, ...]:
    values: list[OcrTableCell] = []
    for cell in _object_sequence(getattr(table, "cells", ())):
        row_index = _non_negative_int(getattr(cell, "row_index", None))
        column_index = _non_negative_int(getattr(cell, "column_index", None))
        content = getattr(cell, "content", None)
        if row_index is None or column_index is None or not isinstance(content, str):
            continue

        values.append(
            OcrTableCell(
                row_index=row_index,
                column_index=column_index,
                row_span=_positive_int(getattr(cell, "row_span", None)) or 1,
                column_span=_positive_int(getattr(cell, "column_span", None)) or 1,
                content=content,
                kind=_optional_text(getattr(cell, "kind", None)),
                spans=_spans(getattr(cell, "spans", ())),
                span_page_number=page_number_override,
                bounding_regions=_bounding_regions(
                    getattr(cell, "bounding_regions", ()),
                    page_number_override=page_number_override,
                ),
            )
        )

    return tuple(values)


def _bounding_regions(
    value: object,
    *,
    page_number_override: int | None,
) -> tuple[OcrBoundingRegion, ...]:
    regions: list[OcrBoundingRegion] = []
    for region in _object_sequence(value):
        page_number = (
            page_number_override
            if page_number_override is not None
            else _positive_int(getattr(region, "page_number", None))
        )
        polygon = _polygon(getattr(region, "polygon", ()))
        if page_number is None or not polygon:
            continue
        regions.append(
            OcrBoundingRegion(
                page_number=page_number,
                bounding_polygon=polygon,
            )
        )
    return tuple(regions)


def _spans(value: object) -> tuple[OcrTextSpan, ...]:
    return tuple(
        span for raw_span in _object_sequence(value) if (span := _span(raw_span)) is not None
    )


def _span(value: object | None) -> OcrTextSpan | None:
    offset = _non_negative_int(getattr(value, "offset", None))
    length = _positive_int(getattr(value, "length", None))
    if offset is None or length is None:
        return None
    return OcrTextSpan(offset=offset, length=length)


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _confidence(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return max(0.0, min(1.0, float(value)))


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    result = round(float(value))
    return result if result > 0 else None


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None


def _polygon(value: object) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()

    coordinates: list[float] = []
    for item in cast(Sequence[object], value):
        if isinstance(item, bool):
            return ()
        if isinstance(item, int | float):
            coordinates.append(round(float(item), 4))
            continue

        x = getattr(item, "x", None)
        y = getattr(item, "y", None)
        if isinstance(x, int | float) and isinstance(y, int | float):
            coordinates.extend((round(float(x), 4), round(float(y), 4)))
            continue
        return ()

    return tuple(coordinates)


def _object_sequence(value: object) -> tuple[object, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    return tuple(cast(Sequence[object], value))
