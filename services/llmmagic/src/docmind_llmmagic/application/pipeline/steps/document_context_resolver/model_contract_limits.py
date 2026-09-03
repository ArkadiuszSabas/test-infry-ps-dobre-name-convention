"""Provider-independent limits for the Context Resolver structured-output contract."""

from collections.abc import Sequence

CONTEXT_RESOLVER_RESOLUTION_VALUES = (
    "present",
    "missing",
    "uncertain",
    "conflicting",
)
CONTEXT_RESOLVER_RESOLUTION_ENUM_VALUE_COUNT = len(CONTEXT_RESOLVER_RESOLUTION_VALUES)
MAX_STRUCTURED_OUTPUT_ENUM_VALUES = 1_000
MAX_EVIDENCE_ENUM_VALUES = (
    MAX_STRUCTURED_OUTPUT_ENUM_VALUES - CONTEXT_RESOLVER_RESOLUTION_ENUM_VALUE_COUNT
)
LARGE_STRING_ENUM_VALUE_THRESHOLD = 250
MAX_LARGE_STRING_ENUM_CHARACTERS = 15_000


def evidence_enum_within_limits(evidence_ids: Sequence[str]) -> bool:
    """Return whether evidence IDs fit the provider's documented enum limits."""

    return evidence_enum_shape_within_limits(
        value_count=len(evidence_ids),
        total_characters=sum(len(evidence_id) for evidence_id in evidence_ids),
    )


def evidence_enum_shape_within_limits(*, value_count: int, total_characters: int) -> bool:
    """Check a pre-counted evidence enum without rebuilding its values."""

    return value_count <= MAX_EVIDENCE_ENUM_VALUES and not (
        value_count > LARGE_STRING_ENUM_VALUE_THRESHOLD
        and total_characters > MAX_LARGE_STRING_ENUM_CHARACTERS
    )
