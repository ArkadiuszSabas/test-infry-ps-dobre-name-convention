"""Deterministic merge and compatibility projection after all OCR decisions."""

from docmind_llmmagic.domain.pipeline.context_resolution import (
    ContextResolutionReasonCode,
    ResolvedAttributeSource,
    ResolvedAttributeSourceKind,
    ResolvedAttributeStatus,
    ResolvedDocumentAttribute,
)

from .config import (
    AgenticAttributeSpec,
    AgenticContextResolverConfig,
)
from .constants import AGENTIC_METADATA_CONFIDENCE
from .document_view import DocumentSource
from .validation import ValidatedDecision

_METADATA_CONTRADICTED_CONFIDENCE_CAP = 0.4
_CONSTRAINT_REJECTION_DIAGNOSTIC_CODES = frozenset(
    {
        "CONSTRAINT_MAX_LENGTH",
        "CONSTRAINT_MAX_VALUE",
        "CONSTRAINT_MIN_LENGTH",
        "CONSTRAINT_MIN_VALUE",
        "CONSTRAINT_PATTERN",
    }
)
_DIAGNOSTIC_REASON_CODE_GROUPS = (
    (
        frozenset({"QUOTE_NOT_FOUND"}),
        ContextResolutionReasonCode.EVIDENCE_QUOTE_NOT_FOUND,
    ),
    (
        frozenset({"TRANSFORMATION_UNVERIFIABLE"}),
        ContextResolutionReasonCode.VALUE_NOT_DERIVABLE,
    ),
    (
        frozenset({"DATA_TYPE_INVALID"}),
        ContextResolutionReasonCode.VALUE_TYPE_MISMATCH,
    ),
    (
        frozenset({"OUTSIDE_ALLOWED_VALUES"}),
        ContextResolutionReasonCode.VALUE_OUTSIDE_DICTIONARY,
    ),
    (
        frozenset({"EVIDENCE_QUOTE_LIMIT_EXCEEDED", "CANDIDATE_LIMIT_EXCEEDED"}),
        ContextResolutionReasonCode.EVIDENCE_TOO_SCATTERED,
    ),
    (
        frozenset({"TIME_BUDGET_EXHAUSTED", "PROVIDER_REQUEST_FAILED"}),
        ContextResolutionReasonCode.FIELD_NOT_PROCESSED,
    ),
)
_PROJECTED_DIAGNOSTIC_CODES = _CONSTRAINT_REJECTION_DIAGNOSTIC_CODES.union(
    code for diagnostic_codes, _ in _DIAGNOSTIC_REASON_CODE_GROUPS for code in diagnostic_codes
)


def compatibility_attributes(
    *,
    config: AgenticContextResolverConfig,
    decisions: tuple[ValidatedDecision, ...],
) -> tuple[ResolvedDocumentAttribute, ...]:
    """Merge AI/manual targets, then mechanically attach external ids by UUID."""

    by_id = {decision.attribute.attribute_id: decision for decision in decisions}
    merged: list[ResolvedDocumentAttribute] = []
    for attribute in config.attributes:
        decision = by_id.get(attribute.attribute_id)
        if attribute.source == "ai":
            if decision is None:
                raise ValueError("AI decision set is incomplete")
            merged.append(_project_ai(config, decision))
        else:
            merged.append(_project_manual(config, attribute))
    return tuple(merged)


def _project_ai(
    config: AgenticContextResolverConfig,
    decision: ValidatedDecision,
) -> ResolvedDocumentAttribute:
    attribute = decision.attribute
    if attribute.metadata_value is not None:
        return _project_metadata_verification(config, decision)
    status = ResolvedAttributeStatus(decision.status)
    reasons = (
        *_reason_codes(attribute, status),
        *_diagnostic_reason_codes(decision),
        *_constraint_reason_codes(decision),
    )
    if _needs_model_output_invalid_reason(decision):
        reasons = (*reasons, ContextResolutionReasonCode.MODEL_OUTPUT_INVALID)
    requires_review = status in {
        ResolvedAttributeStatus.UNCERTAIN,
        ResolvedAttributeStatus.CONFLICTING,
    } or (status == ResolvedAttributeStatus.MISSING and attribute.effective_required)
    requires_review = requires_review or decision.model_output_invalid or decision.requires_review
    return ResolvedDocumentAttribute(
        document_type_id=str(config.document_type_id),
        attribute_external_id=config.compatibility_external_ids[attribute.attribute_id],
        attribute_id=str(attribute.attribute_id),
        display_name=attribute.display_name,
        value_type=attribute.data_type,
        required=attribute.effective_required,
        value=decision.value,
        confidence_score=decision.confidence,
        status=status,
        requires_review=requires_review,
        sources=tuple(_source(item) for item in decision.evidence),
        reason_codes=tuple(dict.fromkeys(reasons)),
    )


def _project_metadata_verification(
    config: AgenticContextResolverConfig,
    decision: ValidatedDecision,
) -> ResolvedDocumentAttribute:
    attribute = decision.attribute
    if attribute.metadata_value is None:
        raise ValueError("metadata verification requires a source value")
    original_status = ResolvedAttributeStatus(decision.status)
    status = (
        ResolvedAttributeStatus.CONFLICTING
        if original_status == ResolvedAttributeStatus.CONFLICTING
        else ResolvedAttributeStatus.PRESENT
    )
    if original_status == ResolvedAttributeStatus.CONFLICTING:
        confidence = min(
            decision.confidence
            if decision.confidence is not None
            else _METADATA_CONTRADICTED_CONFIDENCE_CAP,
            _METADATA_CONTRADICTED_CONFIDENCE_CAP,
        )
    else:
        confidence = AGENTIC_METADATA_CONFIDENCE
    reasons: tuple[ContextResolutionReasonCode, ...] = (
        ContextResolutionReasonCode.VALUE_FROM_SOURCE_SYSTEM,
    )
    if original_status == ResolvedAttributeStatus.CONFLICTING:
        reasons = (
            *reasons,
            ContextResolutionReasonCode.CONFLICTING_VALUES,
            ContextResolutionReasonCode.METADATA_CONTRADICTED,
        )
    reasons = (*reasons, *_diagnostic_reason_codes(decision))
    if _needs_model_output_invalid_reason(decision):
        reasons = (*reasons, ContextResolutionReasonCode.MODEL_OUTPUT_INVALID)
    reasons = (*reasons, *_constraint_reason_codes(decision))
    metadata_not_confirmed = "METADATA_NOT_CONFIRMED" in decision.diagnostic_codes
    requires_review = (
        decision.model_output_invalid
        or original_status == ResolvedAttributeStatus.CONFLICTING
        or (decision.requires_review and not metadata_not_confirmed)
    )
    return ResolvedDocumentAttribute(
        document_type_id=str(config.document_type_id),
        attribute_external_id=config.compatibility_external_ids[attribute.attribute_id],
        attribute_id=str(attribute.attribute_id),
        display_name=attribute.display_name,
        value_type=attribute.data_type,
        required=attribute.effective_required,
        value=attribute.metadata_value,
        confidence_score=confidence,
        status=status,
        requires_review=requires_review,
        sources=(
            ResolvedAttributeSource(kind=ResolvedAttributeSourceKind.DOCUMENT_METADATA),
            *(tuple(_source(item) for item in decision.evidence)),
        ),
        reason_codes=tuple(dict.fromkeys(reasons)),
    )


def _project_manual(
    config: AgenticContextResolverConfig,
    attribute: AgenticAttributeSpec,
) -> ResolvedDocumentAttribute:
    reasons = (ContextResolutionReasonCode.MANUAL_INPUT_REQUIRED,)
    if attribute.effective_required:
        reasons = (*reasons, *_reason_codes(attribute, ResolvedAttributeStatus.MISSING))
    return ResolvedDocumentAttribute(
        document_type_id=str(config.document_type_id),
        attribute_external_id=config.compatibility_external_ids[attribute.attribute_id],
        attribute_id=str(attribute.attribute_id),
        display_name=attribute.display_name,
        value_type=attribute.data_type,
        required=attribute.effective_required,
        value=None,
        confidence_score=None,
        status=ResolvedAttributeStatus.MISSING,
        requires_review=True,
        sources=(),
        reason_codes=tuple(dict.fromkeys(reasons)),
    )


def _reason_codes(
    attribute: AgenticAttributeSpec,
    status: ResolvedAttributeStatus,
) -> tuple[ContextResolutionReasonCode, ...]:
    if status == ResolvedAttributeStatus.CONFLICTING:
        return (ContextResolutionReasonCode.CONFLICTING_VALUES,)
    if status == ResolvedAttributeStatus.UNCERTAIN:
        return (ContextResolutionReasonCode.LOW_CONFIDENCE,)
    if status != ResolvedAttributeStatus.MISSING:
        return ()
    if not attribute.effective_required:
        return (ContextResolutionReasonCode.MISSING_VALUE,)
    if attribute.missing_required_action == "block_approval":
        return (ContextResolutionReasonCode.MISSING_REQUIRED_BLOCK_APPROVAL,)
    return (ContextResolutionReasonCode.MISSING_REQUIRED_REVIEW,)


def _constraint_reason_codes(
    decision: ValidatedDecision,
) -> tuple[ContextResolutionReasonCode, ...]:
    reasons: list[ContextResolutionReasonCode] = []
    if _CONSTRAINT_REJECTION_DIAGNOSTIC_CODES.intersection(decision.diagnostic_codes):
        reasons.append(ContextResolutionReasonCode.ATTRIBUTE_CONSTRAINT_REJECTED)
    if decision.attribute.constraint_warning_codes:
        reasons.append(ContextResolutionReasonCode.ATTRIBUTE_CONSTRAINT_UNSATISFIABLE)
    return tuple(reasons)


def _diagnostic_reason_codes(
    decision: ValidatedDecision,
) -> tuple[ContextResolutionReasonCode, ...]:
    reasons: list[ContextResolutionReasonCode] = []
    for diagnostic_codes, reason in _DIAGNOSTIC_REASON_CODE_GROUPS:
        if diagnostic_codes.intersection(decision.diagnostic_codes):
            reasons.append(reason)
    return tuple(reasons)


def _needs_model_output_invalid_reason(decision: ValidatedDecision) -> bool:
    if not decision.model_output_invalid:
        return False
    return not decision.diagnostic_codes or bool(
        set(decision.diagnostic_codes).difference(_PROJECTED_DIAGNOSTIC_CODES)
    )


def _source(evidence: DocumentSource) -> ResolvedAttributeSource:
    kind = {
        "ocr_key_value": ResolvedAttributeSourceKind.OCR_KEY_VALUE,
        "ocr_line": ResolvedAttributeSourceKind.OCR_LINE,
        "ocr_selection_mark": ResolvedAttributeSourceKind.OCR_SELECTION_MARK,
        "ocr_table_cell": ResolvedAttributeSourceKind.OCR_TABLE_CELL,
        "document_metadata": ResolvedAttributeSourceKind.DOCUMENT_METADATA,
    }.get(evidence.kind, ResolvedAttributeSourceKind.OCR_DOCUMENT)
    return ResolvedAttributeSource(
        kind=kind,
        order_index=evidence.order,
        page_number=evidence.page_number,
        line_number=evidence.line_number,
        key_value_index=evidence.key_value_index,
        confidence=evidence.confidence,
        bounding_polygon=evidence.bounding_polygon or None,
    )
