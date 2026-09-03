"""Deterministic full-document fallback planning and merge operations."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace

from docmind_llmmagic.application.pipeline.steps.document_context_resolver import (
    metadata_priority,
    model_contract_limits,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.config import (
    ContextResolverConfig,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelAttribute,
    ContextResolverModelResult,
    EvidenceUnit,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.retrieval import (
    ContextResolverBatch,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.workflow import (
    ContextResolverWorkflowResult,
)
from docmind_llmmagic.domain.pipeline.context_resolution import (
    ContextAttributeSpec,
    ResolvedAttributeSourceKind,
    ResolvedAttributeStatus,
)

_WHITESPACE = re.compile(r"\s+")
_MAX_MERGED_EVIDENCE_IDS = 16
_MAX_COVERAGE_BATCH_COUNT = 200


@dataclass(frozen=True, slots=True)
class ContextResolverCoverageResult:
    """Merged fallback result and safe coverage metrics."""

    model_result: ContextResolverModelResult
    batch_count: int
    attribute_count: int
    page_count: int
    resolved_attribute_count: int
    conflicting_attribute_count: int
    selected_evidence_unit_count: int
    selected_evidence_char_count: int
    max_batch_attribute_count: int
    model_request_count: int


def requires_coverage_fallback(
    *,
    config: ContextResolverConfig,
    result: ContextResolverWorkflowResult,
) -> bool:
    """Return whether unresolved attributes have OCR evidence left to cover."""

    return bool(
        result.evidence_catalog
        and coverage_attributes(
            config=config,
            primary_result=result.model_result,
        )
    )


def with_coverage_fallback(
    *,
    result: ContextResolverWorkflowResult,
    coverage: ContextResolverCoverageResult,
) -> ContextResolverWorkflowResult:
    """Attach the coverage result and its safe metrics to the primary workflow."""

    metrics = result.metrics
    return ContextResolverWorkflowResult(
        model_result=coverage.model_result,
        evidence_catalog=result.evidence_catalog,
        metrics=replace(
            metrics,
            batch_count=metrics.batch_count + coverage.batch_count,
            model_request_count=metrics.model_request_count + coverage.model_request_count,
            selected_evidence_unit_count=max(
                metrics.selected_evidence_unit_count,
                coverage.selected_evidence_unit_count,
            ),
            selected_evidence_char_count=(
                metrics.selected_evidence_char_count + coverage.selected_evidence_char_count
            ),
            max_batch_attribute_count=max(
                metrics.max_batch_attribute_count,
                coverage.max_batch_attribute_count,
            ),
            coverage_fallback_batch_count=coverage.batch_count,
            coverage_fallback_attribute_count=coverage.attribute_count,
            coverage_fallback_page_count=coverage.page_count,
            coverage_fallback_resolved_attribute_count=coverage.resolved_attribute_count,
            coverage_fallback_conflicting_attribute_count=coverage.conflicting_attribute_count,
        ),
    )


def coverage_attributes(
    *,
    config: ContextResolverConfig,
    primary_result: ContextResolverModelResult,
) -> tuple[ContextAttributeSpec, ...]:
    """Return attributes that remain missing or uncertain after primary extraction."""

    by_id = {attribute.attribute_external_id: attribute for attribute in primary_result.attributes}
    return tuple(
        spec
        for spec in config.attributes
        if _requires_coverage(
            by_id[spec.attribute_external_id],
            low_confidence_threshold=config.low_confidence_threshold,
        )
    )


def plan_coverage_batches(
    attributes: tuple[ContextAttributeSpec, ...],
    evidence: tuple[EvidenceUnit, ...],
    *,
    max_attributes: int,
    max_evidence_chars: int,
) -> tuple[ContextResolverBatch, ...]:
    """Cross bounded attribute groups with ordered evidence windows."""

    metadata = metadata_priority.priority_metadata(evidence)
    metadata_priority.validate_priority_metadata_size(metadata, max_chars=max_evidence_chars)
    metadata_chars = sum(len(unit.text) for unit in metadata)
    non_metadata = tuple(
        unit for unit in evidence if unit.kind != ResolvedAttributeSourceKind.DOCUMENT_METADATA
    )
    windows = _evidence_windows(
        non_metadata,
        max_chars=max_evidence_chars - metadata_chars,
        prefix_evidence_ids=tuple(unit.evidence_id for unit in metadata),
    )
    if not windows:
        windows = ((),)
    attribute_groups = tuple(
        attributes[index : index + max_attributes]
        for index in range(0, len(attributes), max_attributes)
    )
    if len(windows) * len(attribute_groups) > _MAX_COVERAGE_BATCH_COUNT:
        raise safe_context_resolver_error(
            code="CONTEXT_RESOLVER_INPUT_TOO_LARGE",
            message="Context Resolver coverage fallback exceeds the supported batch limit.",
        )
    batches: list[ContextResolverBatch] = []
    for attribute_group in attribute_groups:
        for window in windows:
            batches.append(
                ContextResolverBatch(
                    batch_id=f"coverage-{len(batches) + 1:03d}",
                    attributes=attribute_group,
                    evidence=metadata_priority.prepend_priority_metadata(metadata, window),
                    rejected_candidate_count=0,
                    truncated_candidate_count=0,
                )
            )
    return tuple(batches)


def build_coverage_result(
    *,
    config: ContextResolverConfig,
    primary_result: ContextResolverModelResult,
    batches: tuple[ContextResolverBatch, ...],
    batch_results: tuple[ContextResolverModelResult, ...],
) -> ContextResolverCoverageResult:
    """Merge fallback windows while preserving conclusive primary values."""

    candidates: dict[str, list[ContextResolverModelAttribute]] = {
        spec.attribute_external_id: [] for spec in config.attributes
    }
    for batch, result in zip(batches, batch_results, strict=True):
        expected_ids = {attribute.attribute_external_id for attribute in batch.attributes}
        actual_ids = {attribute.attribute_external_id for attribute in result.attributes}
        if expected_ids != actual_ids:
            _raise_invalid_output()
        for attribute in result.attributes:
            candidates[attribute.attribute_external_id].append(attribute)

    primary_by_id = {
        attribute.attribute_external_id: attribute for attribute in primary_result.attributes
    }
    coverage_attribute_ids = {
        spec.attribute_external_id
        for spec in coverage_attributes(config=config, primary_result=primary_result)
    }
    merged: list[ContextResolverModelAttribute] = []
    resolved_count = 0
    conflicting_count = 0
    for spec in config.attributes:
        primary = primary_by_id[spec.attribute_external_id]
        if spec.attribute_external_id not in coverage_attribute_ids:
            merged.append(primary)
            continue
        fallback = _merge_coverage_candidates(
            primary,
            tuple(candidates[spec.attribute_external_id]),
            low_confidence_threshold=config.low_confidence_threshold,
        )
        merged.append(fallback)
        if fallback.status != ResolvedAttributeStatus.MISSING:
            resolved_count += 1
        if fallback.status == ResolvedAttributeStatus.CONFLICTING:
            conflicting_count += 1

    selected = {unit.evidence_id: unit for batch in batches for unit in batch.evidence}
    page_numbers = {unit.page_number for unit in selected.values() if unit.page_number is not None}
    return ContextResolverCoverageResult(
        model_result=ContextResolverModelResult(attributes=tuple(merged)),
        batch_count=len(batches),
        attribute_count=len(coverage_attribute_ids),
        page_count=len(page_numbers),
        resolved_attribute_count=resolved_count,
        conflicting_attribute_count=conflicting_count,
        selected_evidence_unit_count=len(selected),
        selected_evidence_char_count=sum(
            len(unit.text) for batch in batches for unit in batch.evidence
        ),
        max_batch_attribute_count=max(len(batch.attributes) for batch in batches),
        model_request_count=sum(result.provider_request_count for result in batch_results),
    )


def _evidence_windows(
    evidence: tuple[EvidenceUnit, ...],
    *,
    max_chars: int,
    prefix_evidence_ids: tuple[str, ...] = (),
) -> tuple[tuple[EvidenceUnit, ...], ...]:
    if not model_contract_limits.evidence_enum_within_limits(prefix_evidence_ids):
        _raise_evidence_contract_too_large()
    prefix_evidence_id_chars = sum(len(evidence_id) for evidence_id in prefix_evidence_ids)
    windows: list[tuple[EvidenceUnit, ...]] = []
    current: list[EvidenceUnit] = []
    current_chars = 0
    current_evidence_id_chars = 0
    for unit in evidence:
        unit_chars = len(unit.text)
        if unit_chars > max_chars:
            raise safe_context_resolver_error(
                code="CONTEXT_RESOLVER_INPUT_TOO_LARGE",
                message="Context Resolver OCR evidence exceeds the supported batch limit.",
            )
        candidate_within_contract = model_contract_limits.evidence_enum_shape_within_limits(
            value_count=len(prefix_evidence_ids) + len(current) + 1,
            total_characters=(
                prefix_evidence_id_chars + current_evidence_id_chars + len(unit.evidence_id)
            ),
        )
        if current and (current_chars + unit_chars > max_chars or not candidate_within_contract):
            windows.append(tuple(current))
            current = []
            current_chars = 0
            current_evidence_id_chars = 0
            candidate_within_contract = model_contract_limits.evidence_enum_shape_within_limits(
                value_count=len(prefix_evidence_ids) + 1,
                total_characters=prefix_evidence_id_chars + len(unit.evidence_id),
            )
        if not candidate_within_contract:
            _raise_evidence_contract_too_large()
        current.append(unit)
        current_chars += unit_chars
        current_evidence_id_chars += len(unit.evidence_id)
    if current:
        windows.append(tuple(current))
    return tuple(windows)


def _raise_evidence_contract_too_large() -> None:
    raise safe_context_resolver_error(
        code="CONTEXT_RESOLVER_INPUT_TOO_LARGE",
        message="Context Resolver evidence schema exceeds the supported safe limit.",
    )


def _merge_candidates(
    primary: ContextResolverModelAttribute,
    candidates: tuple[ContextResolverModelAttribute, ...],
) -> ContextResolverModelAttribute:
    present = tuple(
        candidate for candidate in candidates if candidate.status != ResolvedAttributeStatus.MISSING
    )
    if not present:
        return primary

    values = {_normalized_value(candidate.value) for candidate in present}
    conflicting = len(values) > 1 or any(
        candidate.status == ResolvedAttributeStatus.CONFLICTING for candidate in present
    )
    selected = max(
        present,
        key=lambda candidate: (
            candidate.confidence_score if candidate.confidence_score is not None else -1.0
        ),
    )
    evidence_ids = tuple(
        dict.fromkeys(
            evidence_id for candidate in present for evidence_id in candidate.evidence_ids
        )
    )[:_MAX_MERGED_EVIDENCE_IDS]
    return ContextResolverModelAttribute(
        attribute_external_id=primary.attribute_external_id,
        value=selected.value,
        confidence_score=selected.confidence_score,
        status=(
            ResolvedAttributeStatus.CONFLICTING if conflicting else _least_certain_status(present)
        ),
        evidence_ids=evidence_ids,
    )


def _merge_coverage_candidates(
    primary: ContextResolverModelAttribute,
    candidates: tuple[ContextResolverModelAttribute, ...],
    *,
    low_confidence_threshold: float,
) -> ContextResolverModelAttribute:
    normalized_primary = _normalized_primary_status(
        primary,
        low_confidence_threshold=low_confidence_threshold,
    )
    if normalized_primary.status == ResolvedAttributeStatus.MISSING:
        return _merge_candidates(normalized_primary, candidates)
    return _merge_candidates(normalized_primary, (normalized_primary, *candidates))


def _normalized_primary_status(
    primary: ContextResolverModelAttribute,
    *,
    low_confidence_threshold: float,
) -> ContextResolverModelAttribute:
    if primary.status in {
        ResolvedAttributeStatus.MISSING,
        ResolvedAttributeStatus.UNCERTAIN,
    }:
        return primary
    if _requires_coverage(primary, low_confidence_threshold=low_confidence_threshold):
        return replace(primary, status=ResolvedAttributeStatus.UNCERTAIN)
    return primary


def _requires_coverage(
    attribute: ContextResolverModelAttribute,
    *,
    low_confidence_threshold: float,
) -> bool:
    if attribute.status in {
        ResolvedAttributeStatus.MISSING,
        ResolvedAttributeStatus.UNCERTAIN,
    }:
        return True
    if attribute.status == ResolvedAttributeStatus.CONFLICTING:
        return False
    return (
        attribute.value is None
        or attribute.confidence_score is None
        or attribute.confidence_score < low_confidence_threshold
    )


def _least_certain_status(
    candidates: tuple[ContextResolverModelAttribute, ...],
) -> ResolvedAttributeStatus:
    if any(candidate.status == ResolvedAttributeStatus.UNCERTAIN for candidate in candidates):
        return ResolvedAttributeStatus.UNCERTAIN
    return ResolvedAttributeStatus.PRESENT


def _normalized_value(value: str | None) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value or "")).strip().casefold()


def _raise_invalid_output() -> None:
    raise safe_context_resolver_error(
        code="CONTEXT_RESOLVER_MODEL_OUTPUT_INVALID",
        message="Context Resolver model output is invalid.",
    )
