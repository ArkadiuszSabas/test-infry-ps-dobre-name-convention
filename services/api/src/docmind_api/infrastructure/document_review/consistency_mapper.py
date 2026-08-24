"""Map bounded verifier metadata into the product Review consistency contract."""

from collections.abc import Mapping, Sequence
from typing import Any, cast

from docmind_api.application.document_review.read_models import (
    DocumentReviewConsistency,
    DocumentReviewConsistencyAlternative,
    DocumentReviewConsistencyOccurrence,
    DocumentReviewConsistencyStatus,
    not_available_consistency,
)

_MAX_COMPARISON_COUNT = 16
_MAX_VALUE_LENGTH = 4_000
_STATUS_MAP = {
    "consistent": DocumentReviewConsistencyStatus.CONFIRMED,
    "conflicting": DocumentReviewConsistencyStatus.CONFLICTING,
    "not_comparable": DocumentReviewConsistencyStatus.NOT_APPLICABLE,
}
_CONFLICT_REASON_CODES = frozenset(
    {
        "CONFLICTING_VALUES",
        "KV_CONSISTENCY_CONFLICT",
    }
)


def review_consistency_from_context_attribute(
    attribute: Mapping[str, object],
) -> DocumentReviewConsistency:
    """Map verifier data without deriving a partial result from malformed lists."""

    raw_status = _text(attribute.get("consistency_status"))
    status = _STATUS_MAP.get(raw_status) if raw_status is not None else None
    if status is None:
        return not_available_consistency()
    comparison_keys = (
        "compared_values",
        "compared_key_value_pages",
        "compared_key_value_indexes",
    )
    if any(key not in attribute for key in comparison_keys):
        return not_available_consistency()

    values = _texts(attribute.get("compared_values"))
    pages = _positive_ints(attribute.get("compared_key_value_pages"))
    indexes = _positive_ints(attribute.get("compared_key_value_indexes"))
    if values is None or pages is None or indexes is None:
        return not_available_consistency()
    if len(values) != len(pages) or len(values) != len(indexes):
        return not_available_consistency()

    occurrences = tuple(
        DocumentReviewConsistencyOccurrence(page_number=page, key_value_index=index)
        for page, index in zip(pages, indexes, strict=True)
    )
    alternatives = (
        _alternatives(values=values, occurrences=occurrences)
        if status == DocumentReviewConsistencyStatus.CONFLICTING
        else ()
    )
    return DocumentReviewConsistency(
        status=status,
        occurrence_count=len(occurrences),
        confidence_before=_confidence(attribute.get("confidence_before")),
        confidence_after=_confidence(attribute.get("confidence_after")),
        alternatives=alternatives,
    )


def has_invalid_consistency_metadata(attribute: Mapping[str, object]) -> bool:
    """Tell the pipeline source whether verifier metadata makes the whole result unsafe."""

    raw_status = attribute.get("consistency_status")
    if raw_status is None:
        return False
    status_value = _text(raw_status)
    status = _STATUS_MAP.get(status_value) if status_value is not None else None
    if status is None:
        return True
    comparison_keys = (
        "compared_values",
        "compared_key_value_pages",
        "compared_key_value_indexes",
    )
    if any(key not in attribute for key in comparison_keys):
        return True
    values = _texts(attribute.get("compared_values"))
    pages = _positive_ints(attribute.get("compared_key_value_pages"))
    indexes = _positive_ints(attribute.get("compared_key_value_indexes"))
    if values is None or pages is None or indexes is None:
        return True
    if len(values) != len(pages) or len(values) != len(indexes):
        return True
    return status == DocumentReviewConsistencyStatus.CONFLICTING and not (
        _CONFLICT_REASON_CODES.intersection(_reason_codes(attribute.get("reason_codes")))
    )


def _alternatives(
    *,
    values: tuple[str, ...],
    occurrences: tuple[DocumentReviewConsistencyOccurrence, ...],
) -> tuple[DocumentReviewConsistencyAlternative, ...]:
    grouped: dict[str, list[DocumentReviewConsistencyOccurrence]] = {}
    for value, occurrence in zip(values, occurrences, strict=True):
        grouped.setdefault(value, []).append(occurrence)
    return tuple(
        DocumentReviewConsistencyAlternative(value=value, occurrences=tuple(locations))
        for value, locations in grouped.items()
    )


def _texts(value: object) -> tuple[str, ...] | None:
    items = _comparison_items(value)
    if items is None:
        return None
    if len(items) > _MAX_COMPARISON_COUNT:
        return None
    values: list[str] = []
    for item in items:
        text = _text(item, max_length=_MAX_VALUE_LENGTH)
        if text is None:
            return None
        values.append(text)
    return tuple(values)


def _positive_ints(value: object) -> tuple[int, ...] | None:
    items = _comparison_items(value)
    if items is None:
        return None
    if len(items) > _MAX_COMPARISON_COUNT:
        return None
    if any(isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in items):
        return None
    return tuple(cast(int, item) for item in items)


def _reason_codes(value: object) -> tuple[str, ...]:
    return tuple(item for item in _texts(value) or () if item.replace("_", "").isalnum())


def _confidence(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    if value < 0 or value > 1:
        return None
    return round(float(value), 6)


def _text(value: object, *, max_length: int = 32) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped or len(stripped) > max_length:
        return None
    return stripped


def _comparison_items(value: object) -> tuple[object, ...] | None:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(cast(Sequence[Any], value))
    return None
