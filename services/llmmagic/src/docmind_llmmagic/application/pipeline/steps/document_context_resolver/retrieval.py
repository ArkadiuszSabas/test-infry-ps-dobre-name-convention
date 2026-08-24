"""Deterministic candidate retrieval and bounded batch planning."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from docmind_llmmagic.application.pipeline.key_value_matching import (
    normalize_key_value_label,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver import metadata_priority
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    EvidenceUnit,
)
from docmind_llmmagic.domain.pipeline.context_resolution import (
    ContextAttributeSpec,
    ResolvedAttributeSourceKind,
)

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_DATE = re.compile(r"\b(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b")
_NUMBER = re.compile(r"(?<!\w)[+-]?\d[\d\s.,]*(?!\w)")
_CURRENCY = re.compile(r"(?:\b(?:PLN|EUR|USD|GBP|CHF)\b|[$€£])", re.IGNORECASE)
_BOOLEAN = re.compile(r"\b(?:yes|no|true|false|tak|nie)\b", re.IGNORECASE)
_MIN_TOKEN_LENGTH = 3
_MAX_QUERY_TOKEN_COUNT = 48


@dataclass(frozen=True, slots=True)
class CandidateSelection:
    """Bounded evidence selection for one configured attribute."""

    attribute: ContextAttributeSpec
    evidence_ids: tuple[str, ...]
    rejected_count: int
    truncated: bool
    keyword_match: bool
    exact_key_value_match_count: int = 0


@dataclass(frozen=True, slots=True)
class ContextResolverBatch:
    """One deterministic batch with the union of its selected evidence."""

    batch_id: str
    attributes: tuple[ContextAttributeSpec, ...]
    evidence: tuple[EvidenceUnit, ...]
    rejected_candidate_count: int
    truncated_candidate_count: int


@dataclass(frozen=True, slots=True)
class _IndexedEvidence:
    unit: EvidenceUnit
    text: str
    tokens: frozenset[str]
    ordered_tokens: tuple[str, ...]


def retrieve_candidates(
    attributes: tuple[ContextAttributeSpec, ...],
    evidence: tuple[EvidenceUnit, ...],
    *,
    top_k: int,
    max_chars: int,
) -> tuple[CandidateSelection, ...]:
    """Select stable lexical and type-compatible evidence for every attribute."""

    indexed_evidence = tuple(_index_evidence(unit) for unit in evidence)
    return tuple(
        _retrieve_attribute(
            attribute,
            indexed_evidence,
            evidence,
            top_k=top_k,
            max_chars=max_chars,
        )
        for attribute in attributes
    )


def plan_batches(
    selections: tuple[CandidateSelection, ...],
    evidence: tuple[EvidenceUnit, ...],
    *,
    max_attributes: int,
    max_evidence_chars: int,
) -> tuple[ContextResolverBatch, ...]:
    """Preserve configured order while bounding attributes and union evidence per batch."""

    evidence_by_id = {unit.evidence_id: unit for unit in evidence}
    metadata = metadata_priority.priority_metadata(evidence)
    metadata_priority.validate_priority_metadata_size(metadata, max_chars=max_evidence_chars)
    batches: list[ContextResolverBatch] = []
    current: list[CandidateSelection] = []

    for selection in selections:
        proposed = (*current, selection)
        proposed_evidence = _batch_evidence(
            proposed,
            evidence_by_id,
            metadata=metadata,
            max_chars=max_evidence_chars,
        )
        exceeds_attributes = len(proposed) > max_attributes
        exceeds_evidence = _evidence_chars(proposed_evidence) > max_evidence_chars
        if current and (exceeds_attributes or exceeds_evidence):
            batches.append(
                _batch(
                    len(batches) + 1,
                    tuple(current),
                    evidence_by_id,
                    metadata=metadata,
                    max_chars=max_evidence_chars,
                )
            )
            current = [selection]
        else:
            current.append(selection)

    if current:
        batches.append(
            _batch(
                len(batches) + 1,
                tuple(current),
                evidence_by_id,
                metadata=metadata,
                max_chars=max_evidence_chars,
            )
        )
    return tuple(batches)


def _retrieve_attribute(
    attribute: ContextAttributeSpec,
    indexed_evidence: tuple[_IndexedEvidence, ...],
    evidence: tuple[EvidenceUnit, ...],
    *,
    top_k: int,
    max_chars: int,
) -> CandidateSelection:
    exact_labels = frozenset(
        normalized
        for value in (
            attribute.display_name,
            attribute.attribute_external_id,
            *attribute.aliases,
        )
        if (normalized := normalize_key_value_label(value))
    )
    exact_key_values = tuple(
        indexed.unit
        for indexed in indexed_evidence
        if indexed.unit.kind == ResolvedAttributeSourceKind.OCR_KEY_VALUE
        and indexed.unit.label is not None
        and normalize_key_value_label(indexed.unit.label) in exact_labels
    )
    exact_ids = {unit.evidence_id for unit in exact_key_values}
    phrases = _phrases(attribute)
    query_tokens = _query_tokens(attribute)
    scored = [
        (
            _lexical_score(
                indexed,
                phrases=phrases,
                query_tokens=query_tokens,
            ),
            _value_type_score(indexed.text, attribute.value_type),
            indexed.unit,
        )
        for indexed in indexed_evidence
        if indexed.unit.evidence_id not in exact_ids
    ]
    keyword_match = bool(
        exact_key_values
        or any(lexical_score > 0 or type_score > 0 for lexical_score, type_score, _unit in scored)
    )
    ranked = sorted(
        scored,
        key=lambda item: (
            -(2 if item[0] > 0 else 1 if item[1] > 0 else 0),
            -item[0],
            -item[1],
            item[2].order,
        ),
    )

    selected: list[EvidenceUnit] = []
    selected_ids: set[str] = set()
    remaining_chars = max_chars
    for unit in exact_key_values:
        if len(selected) >= top_k:
            break
        if len(unit.text) > remaining_chars:
            continue
        selected.append(unit)
        selected_ids.add(unit.evidence_id)
        remaining_chars -= len(unit.text)

    for _lexical_score_value, _type_score_value, unit in ranked:
        if len(selected) >= top_k:
            break
        if len(unit.text) > remaining_chars:
            continue
        selected.append(unit)
        selected_ids.add(unit.evidence_id)
        remaining_chars -= len(unit.text)

    selected = _with_line_neighbours(
        selected,
        selected_ids,
        evidence,
        top_k=top_k,
        max_chars=max_chars,
    )
    selected.sort(key=lambda unit: unit.order)
    candidate_ids = exact_ids | {
        unit.evidence_id for _lexical_score_value, _type_score_value, unit in ranked
    }
    return CandidateSelection(
        attribute=attribute,
        evidence_ids=tuple(unit.evidence_id for unit in selected),
        rejected_count=max(0, len(evidence) - len(selected)),
        truncated=bool(candidate_ids - selected_ids),
        keyword_match=keyword_match,
        exact_key_value_match_count=len(exact_key_values),
    )


def _lexical_score(
    indexed: _IndexedEvidence,
    *,
    phrases: tuple[tuple[str, ...], ...],
    query_tokens: frozenset[str],
) -> int:
    phrase_score = sum(
        20
        for phrase in phrases
        if phrase and _contains_token_phrase(indexed.ordered_tokens, phrase)
    )
    overlap = len(query_tokens & indexed.tokens)
    score = phrase_score + overlap * 5
    if overlap and indexed.unit.kind == ResolvedAttributeSourceKind.OCR_KEY_VALUE:
        score += 6
    return score


def _value_type_score(text: str, value_type: str | None) -> int:
    validators = {
        "date": _DATE,
        "number": _NUMBER,
        "integer": _NUMBER,
        "currency": _CURRENCY,
        "boolean": _BOOLEAN,
        "identifier": _NUMBER,
    }
    validator = validators.get(value_type or "")
    return 2 if validator is not None and validator.search(text) else 0


def _phrases(attribute: ContextAttributeSpec) -> tuple[tuple[str, ...], ...]:
    values = (attribute.display_name, *attribute.aliases)
    return tuple(
        dict.fromkeys(tokens for value in values if (tokens := _tokens(_normalized_text(value))))
    )


def _query_tokens(attribute: ContextAttributeSpec) -> frozenset[str]:
    values = (
        attribute.display_name,
        *attribute.aliases,
        attribute.extraction_hint or "",
        attribute.llm_context or "",
    )
    tokens: list[str] = []
    for value in values:
        for token in _tokens(_normalized_text(value)):
            if len(token) >= _MIN_TOKEN_LENGTH and token not in tokens:
                tokens.append(token)
            if len(tokens) >= _MAX_QUERY_TOKEN_COUNT:
                return frozenset(tokens)
    return frozenset(tokens)


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(_TOKEN.findall(value))


def _normalized_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _index_evidence(unit: EvidenceUnit) -> _IndexedEvidence:
    text = _normalized_text(unit.text)
    tokens = _tokens(text)
    return _IndexedEvidence(
        unit=unit,
        text=text,
        tokens=frozenset(tokens),
        ordered_tokens=tokens,
    )


def _contains_token_phrase(tokens: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    width = len(phrase)
    return any(tokens[index : index + width] == phrase for index in range(len(tokens) - width + 1))


def _with_line_neighbours(
    selected: list[EvidenceUnit],
    selected_ids: set[str],
    evidence: tuple[EvidenceUnit, ...],
    *,
    top_k: int,
    max_chars: int,
) -> list[EvidenceUnit]:
    by_location = {
        (unit.page_number, unit.line_number): unit
        for unit in evidence
        if unit.kind == ResolvedAttributeSourceKind.OCR_LINE
    }
    remaining_chars = max_chars - sum(len(unit.text) for unit in selected)
    neighbours: list[EvidenceUnit] = []
    for unit in tuple(selected):
        if unit.kind != ResolvedAttributeSourceKind.OCR_LINE or unit.line_number is None:
            continue
        for line_number in (unit.line_number - 1, unit.line_number + 1):
            neighbour = by_location.get((unit.page_number, line_number))
            if neighbour is None or neighbour.evidence_id in selected_ids:
                continue
            if len(selected) + len(neighbours) >= top_k or len(neighbour.text) > remaining_chars:
                continue
            neighbours.append(neighbour)
            selected_ids.add(neighbour.evidence_id)
            remaining_chars -= len(neighbour.text)
    return [*selected, *neighbours]


def _batch(
    index: int,
    selections: tuple[CandidateSelection, ...],
    evidence_by_id: dict[str, EvidenceUnit],
    *,
    metadata: tuple[EvidenceUnit, ...],
    max_chars: int,
) -> ContextResolverBatch:
    return ContextResolverBatch(
        batch_id=f"batch-{index:03d}",
        attributes=tuple(selection.attribute for selection in selections),
        evidence=_batch_evidence(
            selections,
            evidence_by_id,
            metadata=metadata,
            max_chars=max_chars,
        ),
        rejected_candidate_count=sum(selection.rejected_count for selection in selections),
        truncated_candidate_count=sum(selection.truncated for selection in selections),
    )


def _batch_evidence(
    selections: tuple[CandidateSelection, ...],
    evidence_by_id: dict[str, EvidenceUnit],
    *,
    metadata: tuple[EvidenceUnit, ...],
    max_chars: int,
) -> tuple[EvidenceUnit, ...]:
    ids = {evidence_id for selection in selections for evidence_id in selection.evidence_ids}
    selected = tuple(
        sorted(
            (evidence_by_id[evidence_id] for evidence_id in ids),
            key=lambda unit: unit.order,
        )
    )
    metadata_ids = {item.evidence_id for item in metadata}
    remaining_chars = max_chars - _evidence_chars(metadata)
    bounded_selected: list[EvidenceUnit] = []
    for unit in selected:
        if unit.evidence_id in metadata_ids or len(unit.text) > remaining_chars:
            continue
        bounded_selected.append(unit)
        remaining_chars -= len(unit.text)
    return metadata_priority.prepend_priority_metadata(metadata, tuple(bounded_selected))


def _evidence_chars(evidence: tuple[EvidenceUnit, ...]) -> int:
    return sum(len(unit.text) for unit in evidence)
