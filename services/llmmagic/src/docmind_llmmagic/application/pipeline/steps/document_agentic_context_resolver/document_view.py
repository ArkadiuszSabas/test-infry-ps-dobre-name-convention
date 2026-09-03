"""Complete deterministic OCR view and internal quote-to-source map."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from math import isfinite

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrDocumentArtifact,
    OcrDocumentStatus,
    OcrKeyValuePair,
    OcrPageArtifact,
    OcrPageStatus,
    OcrSelectionMark,
    OcrTable,
    OcrTableCell,
    OcrTextLine,
)

from .config import AgenticMetadataSpec

_MAX_CHARS = 2_000_000
_MAX_SEGMENTS = 25_000
_PAGE_HINT_MISS_SCORE_CAP = 0.8
_WHITESPACE = re.compile(r"\s+")
_COMPACT = re.compile(r"[^\w]+", re.UNICODE)
_ATTACHMENT_HEADER = re.compile(
    r"^(?:za(?:ł|l)ącznik|zalacznik|attachment)\s+(?:(?:nr|no)\.?\s*)?(\d{1,4})\b",
    re.IGNORECASE,
)
_MAX_ATTACHMENT_HEADER_LINE_NUMBER = 5
_FULL_PAGE_POLYGON = (0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0)


def _normalized_text(value: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip().casefold()


@dataclass(frozen=True, slots=True)
class DocumentSource:
    """Internal provenance for one model-visible fragment; never exposed as an ID."""

    kind: str
    order: int
    page_number: int | None = None
    line_number: int | None = None
    key_value_index: int | None = None
    confidence: float | None = None
    bounding_polygon: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentViewSegment:
    """One source-backed span inside the complete model-visible document view."""

    text: str
    start: int
    end: int
    sources: tuple[DocumentSource, ...]


@dataclass(frozen=True, slots=True)
class DocumentViewPage:
    """One indivisible page section used by exact provider-request preflight."""

    page_number: int
    text: str
    segments: tuple[DocumentViewSegment, ...]


@dataclass(frozen=True, slots=True)
class QuoteMatch:
    """Deterministic match of a literal model quote back to OCR provenance."""

    quote: str
    matched_text: str
    sources: tuple[DocumentSource, ...]
    score: float
    page_hint_missed: bool
    ambiguous: bool


@dataclass(frozen=True, slots=True)
class DocumentView:
    """Complete OCR view supplied to the model, plus a private source map."""

    text: str
    segments: tuple[DocumentViewSegment, ...]
    pages: tuple[DocumentViewPage, ...]
    structure_text: str = ""
    structure_segments: tuple[DocumentViewSegment, ...] = ()
    metadata_text: str = ""
    metadata_segments: tuple[DocumentViewSegment, ...] = ()
    normalized_text: str = field(default="", repr=False)
    normalized_positions: tuple[int, ...] = field(default=(), repr=False)

    def for_pages(self, page_numbers: tuple[int, ...]) -> DocumentView:
        """Return the same view restricted to complete pages, repeating opted metadata."""

        selected = tuple(page for page in self.pages if page.page_number in set(page_numbers))
        if not selected:
            raise ValueError("document view page selection is empty")
        drafts = [
            (page.text, tuple((segment.text, segment.sources) for segment in page.segments))
            for page in selected
        ]
        return _compose_view(
            drafts,
            self.structure_text,
            self.structure_segments,
            self.metadata_text,
            self.metadata_segments,
        )

    def match_quote(
        self,
        quote: str,
        *,
        page_number: int | None = None,
        allowed_source_kinds: frozenset[str] | None = None,
    ) -> QuoteMatch | None:
        """Find an exact normalized quote, then a conservative punctuation-insensitive match."""

        candidate = quote.strip()
        if not candidate:
            return None
        normalized_quote, _ = _normalized_with_positions(candidate)
        if not normalized_quote:
            return None
        ranges = _find_ranges(
            self.normalized_text,
            normalized_quote,
            self.normalized_positions,
        )
        score = 1.0
        if not ranges:
            compact_view, compact_positions = _compact_with_positions(self.text)
            compact_quote, _ = _compact_with_positions(candidate)
            if len(compact_quote) >= 4:
                ranges = _find_ranges(compact_view, compact_quote, compact_positions)
                score = 0.95
        if not ranges:
            ranges = _fuzzy_segment_ranges(self.segments, candidate)
            score = 0.92
        matches = [
            (start, end, _sources_for_range(self.segments, start, end)) for start, end in ranges
        ]
        if allowed_source_kinds is not None:
            matches = [
                match
                for match in matches
                if any(source.kind in allowed_source_kinds for source in match[2])
            ]
        page_hint_missed = False
        if page_number is not None:
            page_matches = [
                match
                for match in matches
                if any(source.page_number == page_number for source in match[2])
            ]
            page_hint_missed = bool(matches) and not page_matches
            matches = page_matches or matches
        if not matches:
            return None
        start, end, sources = matches[0]
        if not sources:
            return None
        occurrences: dict[tuple[int | None, str], list[frozenset[str]]] = {}
        for match_start, match_end, match_sources in matches:
            key = (
                next((source.page_number for source in match_sources if source.page_number), None),
                _normalized_text(self.text[match_start:match_end]),
            )
            source_kinds = frozenset(source.kind for source in match_sources)
            occurrences.setdefault(key, []).append(source_kinds)
        ambiguous = any(
            any(existing_kinds & source_kinds for existing_kinds in source_kind_sets[:index])
            for source_kind_sets in occurrences.values()
            for index, source_kinds in enumerate(source_kind_sets)
        )
        return QuoteMatch(
            quote=candidate,
            matched_text=self.text[start:end],
            sources=sources,
            score=min(score, _PAGE_HINT_MISS_SCORE_CAP) if page_hint_missed else score,
            page_hint_missed=page_hint_missed,
            ambiguous=ambiguous or len(occurrences) > 1,
        )


def build_document_view(
    artifact: OcrDocumentArtifact,
    *,
    metadata: tuple[AgenticMetadataSpec, ...],
) -> DocumentView:
    """Validate complete OCR and render all structured evidence in document order."""

    _validate_ocr(artifact)
    document_pairs_by_page = _pairs_by_page(artifact)
    tables_by_page = _tables_by_page(artifact.tables)
    page_drafts: list[tuple[str, tuple[tuple[str, tuple[DocumentSource, ...]], ...]]] = []
    attachment_headers: dict[int, DocumentSource] = {}
    order = 0
    for page in sorted(artifact.pages, key=lambda item: item.page_number):
        fragments: list[tuple[str, tuple[DocumentSource, ...]]] = []
        header = f"=== PAGE {page.page_number} ==="
        fragments.append((header, ()))
        line_items = tuple(line for line in page.lines if line.content.strip())
        if line_items:
            fragments.append(("[TEXT]", ()))
            for line_number, line in enumerate(line_items, start=1):
                source = DocumentSource(
                    kind="ocr_line",
                    order=order,
                    page_number=page.page_number,
                    line_number=line_number,
                    confidence=page.confidence,
                    bounding_polygon=_normalized_polygon(
                        line.bounding_polygon,
                        page=page,
                    ),
                )
                fragments.append(
                    (
                        line.content.strip(),
                        (source,),
                    )
                )
                attachment_number = _attachment_header_number(
                    line.content,
                    line_number=line_number,
                )
                if attachment_number is not None:
                    attachment_headers.setdefault(attachment_number, source)
                order += 1
        elif page.text.strip():
            fragments.append(("[TEXT]", ()))
            fragments.append(
                (
                    page.text.strip(),
                    (
                        DocumentSource(
                            kind="ocr_document",
                            order=order,
                            page_number=page.page_number,
                            confidence=page.confidence,
                            bounding_polygon=_FULL_PAGE_POLYGON,
                        ),
                    ),
                )
            )
            order += 1

        pairs = _deduplicated_pairs(
            (*document_pairs_by_page.get(page.page_number, ()), *page.key_value_pairs)
        )
        if pairs:
            fragments.append(("[KEY VALUES]", ()))
            for fallback_index, pair in enumerate(pairs, start=1):
                text = f"{pair.key.strip()}: {pair.value.strip()}".strip(": ")
                fragments.append(
                    (
                        text,
                        (
                            DocumentSource(
                                kind="ocr_key_value",
                                order=order,
                                page_number=page.page_number,
                                key_value_index=pair.order_index or fallback_index,
                                confidence=pair.confidence,
                                bounding_polygon=_normalized_polygon(
                                    pair.bounding_polygon,
                                    page=page,
                                ),
                            ),
                        ),
                    )
                )
                order += 1

        if page.selection_marks:
            fragments.append(("[SELECTION MARKS]", ()))
            for mark_index, mark in enumerate(page.selection_marks, start=1):
                label, line_number = _selection_label(
                    mark,
                    lines=line_items,
                    fallback_order=mark.order_index or mark_index,
                )
                text = f"{label}: {mark.state.value}" if label else mark.state.value
                fragments.append(
                    (
                        text,
                        (
                            DocumentSource(
                                kind="ocr_selection_mark",
                                order=order,
                                page_number=page.page_number,
                                line_number=line_number,
                                confidence=mark.confidence,
                                bounding_polygon=_normalized_polygon(
                                    mark.bounding_region.bounding_polygon,
                                    page=page,
                                ),
                            ),
                        ),
                    )
                )
                order += 1

        page_tables = tables_by_page.get(page.page_number, ())
        if page_tables:
            fragments.append(("[TABLES]", ()))
            for table_number, table in enumerate(page_tables, start=1):
                fragments.append((f"Table {table_number}", ()))
                for row_index in range(table.row_count):
                    cells = sorted(
                        (
                            cell
                            for cell in table.cells
                            if cell.row_index == row_index
                            and page.page_number in _cell_page_numbers(cell, table)
                        ),
                        key=lambda cell: cell.column_index,
                    )
                    row = " | ".join(cell.content.strip() for cell in cells)
                    if not row.strip(" |"):
                        continue
                    sources = tuple(
                        DocumentSource(
                            kind="ocr_table_cell",
                            order=order + cell.column_index,
                            page_number=page.page_number,
                            line_number=_table_cell_line_number(cell, lines=line_items),
                            confidence=page.confidence,
                            bounding_polygon=_normalized_polygon(
                                _cell_polygon_for_page(cell, page_number=page.page_number),
                                page=page,
                            ),
                        )
                        for cell in cells
                    )
                    fragments.append((row, sources))
                    order += max(1, len(cells))
        page_text, page_segments = _render_fragments(tuple(fragments))
        page_drafts.append((page_text, tuple((item.text, item.sources) for item in page_segments)))

    structure_fragments: list[tuple[str, tuple[DocumentSource, ...]]] = []
    if attachment_headers:
        attachment_numbers = tuple(sorted(attachment_headers))
        attachment_sources = tuple(attachment_headers[number] for number in attachment_numbers)
        structure_fragments.extend(
            (
                ("=== DOCUMENT ATTACHMENTS ===", ()),
                (f"Attachment count: {len(attachment_numbers)}", attachment_sources),
                (
                    "Attachment numbers: "
                    + ", ".join(str(number) for number in attachment_numbers),
                    attachment_sources,
                ),
            )
        )
    structure_text, structure_segments = _render_fragments(tuple(structure_fragments))

    metadata_fragments: list[tuple[str, tuple[DocumentSource, ...]]] = []
    if metadata:
        metadata_fragments.append(("=== DOCUMENT METADATA ===", ()))
        for item in metadata:
            metadata_fragments.append(
                (
                    f"{item.display_name}: {item.value}",
                    (DocumentSource(kind="document_metadata", order=order),),
                )
            )
            order += 1
    metadata_text, metadata_segments = _render_fragments(tuple(metadata_fragments))
    view = _compose_view(
        page_drafts,
        structure_text,
        structure_segments,
        metadata_text,
        metadata_segments,
    )
    if not view.segments or len(view.text) > _MAX_CHARS or len(view.segments) > _MAX_SEGMENTS:
        raise safe_context_resolver_error(
            code="AGENTIC_CONTEXT_RESOLVER_INPUT_TOO_LARGE",
            message="Agentic Context Resolver OCR evidence exceeds the supported limit.",
        )
    return view


def _normalized_polygon(
    polygon: tuple[float, ...],
    *,
    page: OcrPageArtifact,
) -> tuple[float, ...]:
    if len(polygon) < 8 or len(polygon) > 16 or len(polygon) % 2 != 0:
        return ()
    if any(not isfinite(coordinate) or coordinate < 0 for coordinate in polygon):
        return ()
    if all(coordinate <= 1 for coordinate in polygon):
        return polygon

    width = page.coordinate_width or page.width_px
    height = page.coordinate_height or page.height_px
    if width is None or height is None or width <= 0 or height <= 0:
        return ()
    normalized = tuple(
        round(coordinate / (width if index % 2 == 0 else height), 6)
        for index, coordinate in enumerate(polygon)
    )
    if any(coordinate < 0 or coordinate > 1 for coordinate in normalized):
        return ()
    return normalized


def _cell_polygon_for_page(
    cell: OcrTableCell,
    *,
    page_number: int,
) -> tuple[float, ...]:
    return next(
        (
            region.bounding_polygon
            for region in cell.bounding_regions
            if region.page_number == page_number
        ),
        (),
    )


def _attachment_header_number(text: str, *, line_number: int) -> int | None:
    if line_number > _MAX_ATTACHMENT_HEADER_LINE_NUMBER:
        return None
    match = _ATTACHMENT_HEADER.match(_WHITESPACE.sub(" ", text).strip())
    if match is None:
        return None
    return int(match.group(1))


def _compose_view(
    page_drafts: list[tuple[str, tuple[tuple[str, tuple[DocumentSource, ...]], ...]]],
    structure_text: str,
    structure_segments: tuple[DocumentViewSegment, ...],
    metadata_text: str,
    metadata_segments: tuple[DocumentViewSegment, ...],
) -> DocumentView:
    text_parts: list[str] = []
    segments: list[DocumentViewSegment] = []
    pages: list[DocumentViewPage] = []
    for page_number, (page_text, page_segment_drafts) in enumerate(page_drafts, start=1):
        if text_parts:
            text_parts.append("\n\n")
        page_start = sum(len(part) for part in text_parts)
        text_parts.append(page_text)
        page_segments: list[DocumentViewSegment] = []
        search_from = 0
        for segment_text, sources in page_segment_drafts:
            if not sources:
                continue
            local_start = page_text.find(segment_text, search_from)
            if local_start < 0:
                continue
            search_from = local_start + len(segment_text)
            item = DocumentViewSegment(
                text=segment_text,
                start=page_start + local_start,
                end=page_start + local_start + len(segment_text),
                sources=sources,
            )
            segments.append(item)
            page_segments.append(item)
        detected = re.match(r"=== PAGE (\d+) ===", page_text)
        actual_page_number = int(detected.group(1)) if detected else page_number
        pages.append(DocumentViewPage(actual_page_number, page_text, tuple(page_segments)))
    rebased_structure: list[DocumentViewSegment] = []
    if structure_text:
        if text_parts:
            text_parts.append("\n\n")
        structure_start = sum(len(part) for part in text_parts)
        text_parts.append(structure_text)
        search_from = 0
        for item in structure_segments:
            local_start = structure_text.find(item.text, search_from)
            if local_start < 0:
                continue
            search_from = local_start + len(item.text)
            rebased = DocumentViewSegment(
                text=item.text,
                start=structure_start + local_start,
                end=structure_start + local_start + len(item.text),
                sources=item.sources,
            )
            rebased_structure.append(rebased)
            segments.append(rebased)
    rebased_metadata: list[DocumentViewSegment] = []
    if metadata_text:
        if text_parts:
            text_parts.append("\n\n")
        metadata_start = sum(len(part) for part in text_parts)
        text_parts.append(metadata_text)
        search_from = 0
        for item in metadata_segments:
            local_start = metadata_text.find(item.text, search_from)
            if local_start < 0:
                continue
            search_from = local_start + len(item.text)
            rebased = DocumentViewSegment(
                text=item.text,
                start=metadata_start + local_start,
                end=metadata_start + local_start + len(item.text),
                sources=item.sources,
            )
            rebased_metadata.append(rebased)
            segments.append(rebased)
    text = "".join(text_parts)
    normalized_text, normalized_positions = _normalized_with_positions(text)
    return DocumentView(
        text=text,
        segments=tuple(segments),
        pages=tuple(pages),
        structure_text=structure_text,
        structure_segments=tuple(rebased_structure),
        metadata_text=metadata_text,
        metadata_segments=tuple(rebased_metadata),
        normalized_text=normalized_text,
        normalized_positions=normalized_positions,
    )


def _render_fragments(
    fragments: tuple[tuple[str, tuple[DocumentSource, ...]], ...],
) -> tuple[str, tuple[DocumentViewSegment, ...]]:
    parts: list[str] = []
    segments: list[DocumentViewSegment] = []
    for text, sources in fragments:
        cleaned = text.strip()
        if not cleaned:
            continue
        if parts:
            parts.append("\n")
        start = sum(len(part) for part in parts)
        parts.append(cleaned)
        if sources:
            segments.append(DocumentViewSegment(cleaned, start, start + len(cleaned), sources))
    return "".join(parts), tuple(segments)


def _validate_ocr(artifact: OcrDocumentArtifact) -> None:
    parsed_pages = tuple(page for page in artifact.pages if page.status == OcrPageStatus.PARSED)
    has_content = bool(
        artifact.key_value_pairs
        or artifact.tables
        or any(page.lines or page.text.strip() or page.selection_marks for page in parsed_pages)
    )
    if (
        artifact.status != OcrDocumentStatus.SUCCEEDED
        or artifact.total_page_count <= 0
        or artifact.succeeded_page_count != artifact.total_page_count
        or artifact.failed_page_count
        or len(parsed_pages) != artifact.total_page_count
        or {page.page_number for page in parsed_pages}
        != set(range(1, artifact.total_page_count + 1))
        or not has_content
    ):
        raise safe_context_resolver_error(
            code="AGENTIC_CONTEXT_RESOLVER_OCR_INCOMPLETE",
            message="Agentic Context Resolver requires complete searchable OCR output.",
        )


def _pairs_by_page(artifact: OcrDocumentArtifact) -> dict[int, tuple[OcrKeyValuePair, ...]]:
    result: dict[int, list[OcrKeyValuePair]] = {}
    for pair in artifact.key_value_pairs:
        result.setdefault(pair.page_number, []).append(pair)
    return {page: tuple(items) for page, items in result.items()}


def _deduplicated_pairs(
    pairs: tuple[OcrKeyValuePair, ...],
) -> tuple[OcrKeyValuePair, ...]:
    result: list[OcrKeyValuePair] = []
    seen: set[tuple[object, ...]] = set()
    for pair in pairs:
        key = (
            pair.key.strip().casefold(),
            pair.value.strip().casefold(),
            pair.page_number,
        )
        if key not in seen:
            seen.add(key)
            result.append(pair)
    return tuple(result)


def _tables_by_page(tables: tuple[OcrTable, ...]) -> dict[int, tuple[OcrTable, ...]]:
    result: dict[int, list[OcrTable]] = {}
    for table in tables:
        pages = {region.page_number for region in table.bounding_regions} or (
            {table.span_page_number} if table.span_page_number is not None else set()
        )
        if not pages:
            pages = {
                region.page_number for cell in table.cells for region in cell.bounding_regions
            } or {
                cell.span_page_number for cell in table.cells if cell.span_page_number is not None
            }
        if not pages:
            pages = {1}
        for page_number in pages:
            result.setdefault(page_number, []).append(table)
    return {page: tuple(items) for page, items in result.items()}


def _cell_page_numbers(cell: OcrTableCell, table: OcrTable) -> frozenset[int]:
    explicit = {region.page_number for region in cell.bounding_regions}
    if explicit:
        return frozenset(explicit)
    if cell.span_page_number is not None:
        return frozenset({cell.span_page_number})
    if table.span_page_number is not None:
        return frozenset({table.span_page_number})
    table_pages = {region.page_number for region in table.bounding_regions}
    return frozenset({min(table_pages) if table_pages else 1})


def _selection_label(
    mark: OcrSelectionMark,
    *,
    lines: tuple[OcrTextLine, ...],
    fallback_order: int,
) -> tuple[str, int | None]:
    if not lines:
        return f"Selection {fallback_order}", None
    mark_polygon = mark.bounding_region.bounding_polygon
    if not mark_polygon:
        index = min(max(fallback_order - 1, 0), len(lines) - 1)
        return lines[index].content.strip(), index + 1
    mark_y = sum(mark_polygon[1::2]) / max(1, len(mark_polygon[1::2]))
    ranked: list[tuple[float, int, str]] = []
    for index, line in enumerate(lines):
        line_y = (
            sum(line.bounding_polygon[1::2]) / max(1, len(line.bounding_polygon[1::2]))
            if line.bounding_polygon
            else float(index)
        )
        ranked.append((abs(line_y - mark_y), index, line.content.strip()))
    _, index, label = min(ranked)
    return label, index + 1


def _table_cell_line_number(
    cell: OcrTableCell,
    *,
    lines: tuple[OcrTextLine, ...],
) -> int | None:
    """Recover the closest OCR line as a compatibility hint beside the exact polygon."""

    if not lines:
        return None
    cell_text = _WHITESPACE.sub(" ", cell.content).strip().casefold()
    text_matches = [
        index
        for index, line in enumerate(lines)
        if cell_text and cell_text in _WHITESPACE.sub(" ", line.content).strip().casefold()
    ]
    polygon = cell.bounding_regions[0].bounding_polygon if cell.bounding_regions else ()
    candidates = text_matches or list(range(len(lines)))
    if not polygon:
        return candidates[0] + 1
    cell_y = sum(polygon[1::2]) / max(1, len(polygon[1::2]))

    def distance(index: int) -> tuple[float, int]:
        line_polygon = lines[index].bounding_polygon
        line_y = (
            sum(line_polygon[1::2]) / max(1, len(line_polygon[1::2]))
            if line_polygon
            else float(index)
        )
        return abs(line_y - cell_y), index

    return min(candidates, key=distance) + 1


def _normalized_with_positions(value: str) -> tuple[str, tuple[int, ...]]:
    output: list[str] = []
    positions: list[int] = []
    pending_space: tuple[str, int] | None = None
    for index, character in enumerate(value):
        normalized = unicodedata.normalize("NFKC", character).casefold()
        for item in normalized:
            if item.isspace():
                pending_space = (" ", index)
                continue
            if pending_space is not None and output:
                output.append(" ")
                positions.append(pending_space[1])
            pending_space = None
            output.append(item)
            positions.append(index)
    return "".join(output), tuple(positions)


def _compact_with_positions(value: str) -> tuple[str, tuple[int, ...]]:
    normalized, positions = _normalized_with_positions(value)
    output: list[str] = []
    compact_positions: list[int] = []
    for index, character in enumerate(normalized):
        for item in unicodedata.normalize("NFKD", character):
            if not unicodedata.combining(item) and not _COMPACT.fullmatch(item):
                output.append(item)
                compact_positions.append(positions[index])
    return "".join(output), tuple(compact_positions)


def _find_ranges(
    source: str,
    needle: str,
    positions: tuple[int, ...],
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 0
    while (found := source.find(needle, start)) >= 0:
        ranges.append((positions[found], positions[found + len(needle) - 1] + 1))
        start = found + 1
    return ranges


def _fuzzy_segment_ranges(
    segments: tuple[DocumentViewSegment, ...],
    quote: str,
) -> list[tuple[int, int]]:
    quote_normalized = _WHITESPACE.sub(" ", quote).strip().casefold()
    ranked: list[tuple[float, int, int]] = []
    for segment in segments:
        segment_normalized = _WHITESPACE.sub(" ", segment.text).strip().casefold()
        ratio = SequenceMatcher(None, quote_normalized, segment_normalized).ratio()
        if ratio >= 0.92:
            ranked.append((ratio, segment.start, segment.end))
    if not ranked:
        return []
    best = max(item[0] for item in ranked)
    return [(start, end) for ratio, start, end in ranked if ratio == best]


def _sources_for_range(
    segments: tuple[DocumentViewSegment, ...],
    start: int,
    end: int,
) -> tuple[DocumentSource, ...]:
    sources: list[DocumentSource] = []
    seen: set[DocumentSource] = set()
    for segment in segments:
        if segment.end <= start or segment.start >= end:
            continue
        for source in segment.sources:
            if source not in seen:
                seen.add(source)
                sources.append(source)
    return tuple(sorted(sources, key=lambda item: item.order))
