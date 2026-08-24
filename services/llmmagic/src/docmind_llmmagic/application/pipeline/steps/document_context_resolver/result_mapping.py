"""Deterministic mapping from validated model batches to the public domain artifact."""

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.config import (
    ContextResolverConfig,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelAttribute,
    ContextResolverModelResult,
    EvidenceUnit,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.validation import (
    validate_reason_codes,
)
from docmind_llmmagic.domain.pipeline.context_resolution import (
    ContextAttributeSpec,
    ContextResolutionReasonCode,
    ResolvedAttributeSource,
    ResolvedAttributeSourceKind,
    ResolvedAttributeStatus,
    ResolvedDocumentAttribute,
)


def resolved_attributes(
    *,
    config: ContextResolverConfig,
    model_result: ContextResolverModelResult,
    evidence_catalog: tuple[EvidenceUnit, ...],
) -> tuple[ResolvedDocumentAttribute, ...]:
    """Map the exact validated result in configured order."""

    model_by_id = {
        attribute.attribute_external_id: attribute for attribute in model_result.attributes
    }
    evidence_by_id = {unit.evidence_id: unit for unit in evidence_catalog}
    return tuple(
        _resolved_attribute(
            config=config,
            spec=spec,
            model_attribute=model_by_id[spec.attribute_external_id],
            evidence_by_id=evidence_by_id,
        )
        for spec in config.attributes
    )


def _resolved_attribute(
    *,
    config: ContextResolverConfig,
    spec: ContextAttributeSpec,
    model_attribute: ContextResolverModelAttribute,
    evidence_by_id: dict[str, EvidenceUnit],
) -> ResolvedDocumentAttribute:
    value = _safe_value(model_attribute.value)
    confidence = _safe_confidence(model_attribute.confidence_score)
    status = _resolved_status(
        model_attribute=model_attribute,
        value=value,
        confidence=confidence,
        low_confidence_threshold=config.low_confidence_threshold,
    )
    reason_codes = _reason_codes(
        spec=spec,
        value=value,
        confidence=confidence,
        status=status,
        low_confidence_threshold=config.low_confidence_threshold,
    )
    return ResolvedDocumentAttribute(
        document_type_id=config.document_type_id,
        attribute_external_id=spec.attribute_external_id,
        attribute_id=spec.attribute_id,
        display_name=spec.display_name,
        aliases=spec.aliases,
        value_type=spec.value_type,
        required=spec.required,
        value=value,
        confidence_score=confidence,
        status=status,
        requires_review=bool(reason_codes) or status != ResolvedAttributeStatus.PRESENT,
        sources=_sources(model_attribute, evidence_by_id=evidence_by_id),
        reason_codes=reason_codes,
    )


def _resolved_status(
    *,
    model_attribute: ContextResolverModelAttribute,
    value: str | None,
    confidence: float | None,
    low_confidence_threshold: float,
) -> ResolvedAttributeStatus:
    if value is None:
        return ResolvedAttributeStatus.MISSING
    if model_attribute.status == ResolvedAttributeStatus.CONFLICTING:
        return ResolvedAttributeStatus.CONFLICTING
    if (
        model_attribute.status == ResolvedAttributeStatus.UNCERTAIN
        or confidence is None
        or confidence < low_confidence_threshold
    ):
        return ResolvedAttributeStatus.UNCERTAIN
    return ResolvedAttributeStatus.PRESENT


def _reason_codes(
    *,
    spec: ContextAttributeSpec,
    value: str | None,
    confidence: float | None,
    status: ResolvedAttributeStatus,
    low_confidence_threshold: float,
) -> tuple[ContextResolutionReasonCode, ...]:
    values: list[ContextResolutionReasonCode] = []
    if spec.attribute_id is None:
        values.append(ContextResolutionReasonCode.ATTRIBUTE_MAPPING_MISSING)
    if value is None:
        values.append(
            ContextResolutionReasonCode.MISSING_REQUIRED_VALUE
            if spec.required
            else ContextResolutionReasonCode.MISSING_VALUE
        )
    if status == ResolvedAttributeStatus.CONFLICTING:
        values.append(ContextResolutionReasonCode.CONFLICTING_VALUES)
    if value is not None and (confidence is None or confidence < low_confidence_threshold):
        values.append(ContextResolutionReasonCode.LOW_CONFIDENCE)
    result = tuple(dict.fromkeys(values))
    validate_reason_codes(result)
    return result


def _sources(
    model_attribute: ContextResolverModelAttribute,
    *,
    evidence_by_id: dict[str, EvidenceUnit],
) -> tuple[ResolvedAttributeSource, ...]:
    if model_attribute.status == ResolvedAttributeStatus.MISSING:
        return (ResolvedAttributeSource(kind=ResolvedAttributeSourceKind.MISSING),)
    return tuple(
        _source(evidence_by_id[evidence_id]) for evidence_id in model_attribute.evidence_ids
    )


def _source(unit: EvidenceUnit) -> ResolvedAttributeSource:
    return ResolvedAttributeSource(
        kind=unit.kind,
        page_number=unit.page_number,
        line_number=unit.line_number,
        key_value_index=unit.key_value_index,
        confidence=_safe_confidence(unit.confidence),
    )


def _safe_value(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def _safe_confidence(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return round(max(0.0, min(1.0, float(value))), 6)
