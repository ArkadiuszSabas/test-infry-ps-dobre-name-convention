"""Safe deterministic fallbacks after the single bounded repair attempt."""

from .config import AgenticAttributeSpec
from .validation import AgenticValidationIssue, ValidatedDecision

# These two policies are deliberately separate. A grounded, type-valid semantic value may
# remain uncertain; quote/type/contract failures must never retain a value.
_SAFE_UNCERTAIN_FALLBACK_CODES = frozenset({"AMBIGUOUS_GROUNDED_VALUE"})
_EMPTY_VALIDATION_FALLBACK_CODES = frozenset(
    {
        "CANDIDATE_LIMIT_EXCEEDED",
        "CONFIDENCE_INVALID",
        "CONFLICT_INCOMPLETE",
        "CONSTRAINT_MAX_LENGTH",
        "CONSTRAINT_MAX_VALUE",
        "CONSTRAINT_MIN_LENGTH",
        "CONSTRAINT_MIN_VALUE",
        "CONSTRAINT_PATTERN",
        "DATA_TYPE_INVALID",
        "DERIVATION_INVALID",
        "EVIDENCE_QUOTE_LIMIT_EXCEEDED",
        "EXACT_HANDLE_SET_MISMATCH",
        "MISSING_FIELDS_INCOMPATIBLE",
        "OUTSIDE_ALLOWED_VALUES",
        "OUTPUT_CONTRACT_VIOLATION",
        "QUOTE_NOT_FOUND",
        "SELECTED_CANDIDATE_INVALID",
        "STATUS_INVALID",
        "TRANSFORMATION_UNVERIFIABLE",
        "VALUE_REQUIRED",
    }
)


def empty_validation_fallback(
    *,
    attributes: tuple[AgenticAttributeSpec, ...],
    issues: tuple[AgenticValidationIssue, ...],
    output_error_code: str | None = None,
) -> tuple[ValidatedDecision, ...]:
    """Leave invalid values empty, at zero confidence, and explicitly review-required."""

    issue_handles = {issue.handle for issue in issues if issue.handle is not None}
    group_issue = any(issue.handle is None for issue in issues)
    codes_by_handle = {
        attribute.handle: tuple(
            sorted(
                {issue.code for issue in issues if group_issue or issue.handle == attribute.handle}
                | ({output_error_code} if output_error_code is not None else set())
            )
        )
        for attribute in attributes
    }
    selected = tuple(
        attribute
        for attribute in attributes
        if group_issue or output_error_code is not None or attribute.handle in issue_handles
    )
    return tuple(
        ValidatedDecision(
            attribute=attribute,
            status="missing",
            value=None,
            evidence=(),
            confidence=0.0,
            model_output_invalid=True,
            requires_review=True,
            diagnostic_codes=codes_by_handle[attribute.handle] or ("OUTPUT_CONTRACT_VIOLATION",),
        )
        for attribute in selected
    )
