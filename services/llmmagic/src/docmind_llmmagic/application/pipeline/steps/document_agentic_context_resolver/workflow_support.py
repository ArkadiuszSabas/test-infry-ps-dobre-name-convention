"""Pure target, merge, and content-free repair helpers for Agentic CR."""

import re
import unicodedata
from dataclasses import replace

from .aggregate_values import aggregate_values_equivalent
from .config import AgenticAttributeSpec
from .constants import AGENTIC_METADATA_NOT_CONFIRMED_CONFIDENCE
from .ports import AgenticModelTarget
from .validation import AgenticValidationError, ValidatedDecision

_WHITESPACE = re.compile(r"\s+")
_COVERAGE_PENDING_CODE = "SECOND_PASS_REQUIRED"
_BUSINESS_MISSING = "BUSINESS_MISSING"
_SECOND_PASS_DIVERGED_CODE = "SECOND_PASS_DIVERGED"
_METADATA_NOT_CONFIRMED = "METADATA_NOT_CONFIRMED"


def model_target(attribute: AgenticAttributeSpec) -> AgenticModelTarget:
    """Project one configuration target without UUIDs or integration-only identifiers."""

    return AgenticModelTarget(
        handle=attribute.handle,
        display_name=attribute.display_name,
        data_type=attribute.data_type,
        value_source=attribute.value_source,
        constraints=dict(attribute.constraints),
        allowed_values=(*attribute.allowed_values, *attribute.dictionary_values),
        llm_context=attribute.llm_context,
        metadata_value=attribute.metadata_value,
    )


def merge_decisions(
    attributes: tuple[AgenticAttributeSpec, ...],
    *groups: tuple[ValidatedDecision, ...],
) -> tuple[ValidatedDecision, ...]:
    """Merge independently valid and repaired decisions in configuration order."""

    by_handle = {decision.attribute.handle: decision for group in groups for decision in group}
    return tuple(by_handle[item.handle] for item in attributes if item.handle in by_handle)


def requires_second_pass(
    decision: ValidatedDecision,
    *,
    present_confidence_threshold: float,
) -> bool:
    """Select coverage targets deterministically without retrying technical fallbacks."""

    if decision.model_output_invalid or decision.status == "conflicting":
        return False
    if decision.status in {"missing", "uncertain"}:
        return True
    return (
        decision.status == "present"
        and present_confidence_threshold > 0.0
        and (decision.confidence is None or decision.confidence < present_confidence_threshold)
    )


def merge_second_pass_decisions(
    attributes: tuple[AgenticAttributeSpec, ...],
    primary: tuple[ValidatedDecision, ...],
    secondary: tuple[ValidatedDecision, ...],
    *,
    present_confidence_threshold: float,
) -> tuple[ValidatedDecision, ...]:
    """Merge a deterministic coverage pass by confidence and detect value conflicts."""

    primary_by_handle = {decision.attribute.handle: decision for decision in primary}
    secondary_by_handle = {decision.attribute.handle: decision for decision in secondary}
    merged: list[ValidatedDecision] = []
    for attribute in attributes:
        first = primary_by_handle[attribute.handle]
        second = secondary_by_handle.get(attribute.handle)
        if second is None:
            merged.append(first)
            continue
        normalized_first = _normalized_primary_status(
            first,
            present_confidence_threshold=present_confidence_threshold,
        )
        merged.append(_merge_second_pass_decision(normalized_first, second))
    return tuple(merged)


def _normalized_primary_status(
    decision: ValidatedDecision,
    *,
    present_confidence_threshold: float,
) -> ValidatedDecision:
    if (
        decision.status == "present"
        and present_confidence_threshold > 0.0
        and (decision.confidence is None or decision.confidence < present_confidence_threshold)
    ):
        return replace(decision, status="uncertain", requires_review=True)
    return decision


def _merge_second_pass_decision(
    primary: ValidatedDecision,
    secondary: ValidatedDecision,
) -> ValidatedDecision:
    if secondary.model_output_invalid:
        return secondary if primary.status == "missing" else primary
    if secondary.status == "missing":
        if primary.status == "missing":
            if secondary.attribute.metadata_value is not None:
                return replace(
                    secondary,
                    status="present",
                    value=secondary.attribute.metadata_value,
                    confidence=AGENTIC_METADATA_NOT_CONFIRMED_CONFIDENCE,
                    requires_review=True,
                    diagnostic_codes=(_METADATA_NOT_CONFIRMED,),
                )
            return replace(
                secondary,
                requires_review=secondary.attribute.effective_required,
                diagnostic_codes=(_BUSINESS_MISSING,),
            )
        return primary
    if primary.status == "missing" or primary.model_output_invalid:
        return replace(
            secondary,
            diagnostic_codes=_without_coverage_pending(secondary.diagnostic_codes),
        )

    candidates = (primary, secondary)
    selected = max(
        candidates,
        key=lambda decision: decision.confidence if decision.confidence is not None else -1.0,
    )
    values_agree_across_passes = _values_agree_across_passes(primary, secondary)
    values_diverged_across_passes = not values_agree_across_passes
    inherited_conflicting_status = any(item.status == "conflicting" for item in candidates)
    conflicting = inherited_conflicting_status
    status = (
        "conflicting"
        if conflicting
        else "uncertain"
        if values_diverged_across_passes or any(item.status == "uncertain" for item in candidates)
        else "present"
    )
    confidence = selected.confidence
    if confidence is not None:
        if status == "conflicting":
            confidence = min(confidence, 0.6)
        elif status == "uncertain":
            confidence = min(confidence, 0.7)
    diagnostic_codes = list(
        dict.fromkeys(code for decision in candidates for code in decision.diagnostic_codes)
    )
    if values_diverged_across_passes and status != "conflicting":
        diagnostic_codes.append(_SECOND_PASS_DIVERGED_CODE)
    evidence = (
        tuple(dict.fromkeys(source for decision in candidates for source in decision.evidence))
        if values_agree_across_passes
        else selected.evidence
    )
    evidence_quotes = (
        tuple(dict.fromkeys(quote for decision in candidates for quote in decision.evidence_quotes))
        if values_agree_across_passes
        else selected.evidence_quotes
    )
    return replace(
        selected,
        status=status,
        evidence=evidence,
        evidence_quotes=evidence_quotes,
        confidence=confidence,
        model_output_invalid=False,
        requires_review=status in {"uncertain", "conflicting"},
        diagnostic_codes=_without_coverage_pending(tuple(diagnostic_codes)),
        quote_reference_count=sum(item.quote_reference_count for item in candidates),
        candidate_count=max(item.candidate_count for item in candidates),
    )


def _without_coverage_pending(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(code for code in codes if code != _COVERAGE_PENDING_CODE)


def _normalized_value(value: str | None) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value or "")).strip().casefold()


def _values_agree_across_passes(
    primary: ValidatedDecision,
    secondary: ValidatedDecision,
) -> bool:
    if _normalized_value(primary.value) == _normalized_value(secondary.value):
        return True
    return (
        primary.derivation == "aggregate"
        and secondary.derivation == "aggregate"
        and aggregate_values_equivalent(primary.value or "", secondary.value or "")
    )


def repair_message(error: AgenticValidationError) -> str:
    """Build a content-free repair instruction from allowlisted validation codes."""

    issues = " ".join(
        (
            f"{issue.handle or 'group'}:{issue.code} "
            f"derivation={issue.derivation or 'not-declared'} reason={issue.reason}."
        )
        for issue in error.issues
    )
    guidance = {
        "CANDIDATE_LIMIT_EXCEEDED": "Return at most eight candidates.",
        "CONFIDENCE_INVALID": "Return confidence between zero and one.",
        "CONFLICT_INCOMPLETE": "Return at least two distinct quote-grounded candidates.",
        "CONSTRAINT_MAX_LENGTH": "Return a value no longer than the configured maximum length.",
        "CONSTRAINT_MAX_VALUE": "Return a value at most the configured maximum value.",
        "CONSTRAINT_MIN_LENGTH": "Return a value at least the configured minimum length.",
        "CONSTRAINT_MIN_VALUE": "Return a value at least the configured minimum value.",
        "CONSTRAINT_PATTERN": "Return a value matching the configured pattern.",
        "DATA_TYPE_INVALID": "Return the exact configured canonical data type.",
        "DERIVATION_INVALID": "Use only a supported derivation.",
        "EVIDENCE_QUOTE_LIMIT_EXCEEDED": "Use at most sixteen short quotes per candidate.",
        "EXACT_HANDLE_SET_MISMATCH": "Return exactly the requested handles.",
        "METADATA_CONFIRMATION_VALUE_INVALID": (
            "For confirmed metadata return the exact supplied metadata_value."
        ),
        "METADATA_CONTRADICTION_INCOMPLETE": (
            "For contradicted metadata return a different document value and its quote."
        ),
        "METADATA_VERIFICATION_STATUS_INVALID": (
            "For metadata verification use present, conflicting, or missing."
        ),
        "OUTSIDE_ALLOWED_VALUES": "Return one of the supplied allowed values.",
        "QUOTE_NOT_FOUND": "Copy literal quotes exactly from the supplied document view.",
        "SELECTED_CANDIDATE_INVALID": "Put the selected candidate first.",
        "TRANSFORMATION_UNVERIFIABLE": "Use a value deterministically supported by its quotes.",
        "VALUE_REQUIRED": "Return a quote-grounded candidate for a non-missing result.",
    }
    instructions = " ".join(
        dict.fromkeys(
            guidance.get(issue.code, "Satisfy the strict result contract.")
            for issue in error.issues
        )
    )
    return (
        "Return corrected final decisions only for the requested handles. "
        f"Validation failures: {issues} {instructions} "
        "For each failed handle, you may fall back to derivation=verbatim with a longer literal "
        "quote containing the exact value, or return missing if the value is genuinely absent "
        "from the complete document view. Never invent quotes or values."
    )
