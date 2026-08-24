"""Recover ordered OCR sources that the Context Resolver omitted."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from docmind_llmmagic.domain.pipeline.context_resolution import (
    ResolvedAttributeSource,
    ResolvedAttributeSourceKind,
    ResolvedDocumentAttribute,
)
from docmind_llmmagic.domain.pipeline.ocr import OcrPageArtifact

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class _LineCandidate:
    page_number: int
    line_number: int
    score: int


def recover_ordered_source(
    attribute: ResolvedDocumentAttribute,
    *,
    matching_key_values: tuple[tuple[int, int], ...],
    values_by_source: dict[tuple[int, int], tuple[str, str]],
    pages: tuple[OcrPageArtifact, ...],
    normalize_value: Callable[[str, str | None], str],
) -> ResolvedAttributeSource | None:
    """Return one unambiguous OCR source only when it agrees with the extracted value."""

    if _has_ordered_ocr_source(attribute) or attribute.value is None:
        return None

    matching_value_keys = tuple(
        source_key
        for source_key in matching_key_values
        if normalize_value(values_by_source[source_key][1], attribute.value_type)
        == normalize_value(attribute.value, attribute.value_type)
    )
    if len(matching_value_keys) == 1:
        page_number, key_value_index = matching_value_keys[0]
        return ResolvedAttributeSource(
            kind=ResolvedAttributeSourceKind.OCR_KEY_VALUE,
            page_number=page_number,
            key_value_index=key_value_index,
        )
    if matching_value_keys:
        return None

    return _best_line_source(attribute, pages=pages, normalize_value=normalize_value)


def _best_line_source(
    attribute: ResolvedDocumentAttribute,
    *,
    pages: tuple[OcrPageArtifact, ...],
    normalize_value: Callable[[str, str | None], str],
) -> ResolvedAttributeSource | None:
    assert attribute.value is not None
    labels = tuple(
        normalized
        for label in (attribute.display_name, *attribute.aliases, attribute.attribute_external_id)
        if (normalized := _normalized_text(label))
    )
    value = normalize_value(attribute.value, attribute.value_type)
    if not labels or not value:
        return None

    candidates: list[_LineCandidate] = []
    for page in pages:
        normalized_lines = tuple(_normalized_text(line.content) for line in page.lines)
        for index, line in enumerate(normalized_lines):
            label_match = any(label in line for label in labels)
            value_match = _value_matches(
                line,
                value=value,
                value_type=attribute.value_type,
                normalize_value=normalize_value,
            )
            nearby_value_match = any(
                _value_matches(
                    candidate,
                    value=value,
                    value_type=attribute.value_type,
                    normalize_value=normalize_value,
                )
                for candidate in normalized_lines[max(0, index - 1) : index + 2]
            )
            if label_match and value_match:
                score = 300
            elif label_match and nearby_value_match:
                score = 200
            else:
                continue
            candidates.append(
                _LineCandidate(page.page_number, index + 1, score),
            )

    if not candidates:
        return None
    best_score = max(candidate.score for candidate in candidates)
    best = tuple(candidate for candidate in candidates if candidate.score == best_score)
    if len(best) != 1:
        return None
    return ResolvedAttributeSource(
        kind=ResolvedAttributeSourceKind.OCR_LINE,
        page_number=best[0].page_number,
        line_number=best[0].line_number,
    )


def _has_ordered_ocr_source(attribute: ResolvedDocumentAttribute) -> bool:
    return any(
        (
            source.kind == ResolvedAttributeSourceKind.OCR_KEY_VALUE
            and source.page_number is not None
            and source.key_value_index is not None
        )
        or (
            source.kind == ResolvedAttributeSourceKind.OCR_LINE
            and source.page_number is not None
            and source.line_number is not None
        )
        for source in attribute.sources
    )


def _normalized_text(value: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip().casefold()


def _value_matches(
    line: str,
    *,
    value: str,
    value_type: str | None,
    normalize_value: Callable[[str, str | None], str],
) -> bool:
    if value in line:
        return True
    return "id" in (value_type or "").casefold() and value in normalize_value(line, value_type)
