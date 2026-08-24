"""Exact-contract mapping for one Context Resolver model batch."""

import math
from collections.abc import Mapping, Sequence
from typing import cast

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelAttribute,
    ContextResolverModelResult,
)
from docmind_llmmagic.domain.pipeline.context_resolution import ResolvedAttributeStatus

_TOP_LEVEL_KEYS = frozenset({"results"})
_RESULT_KEYS = frozenset({"value", "confidence", "evidence_ids", "resolution"})
_MAX_VALUE_CHARS = 4_000
_MAX_EVIDENCE_COUNT = 16


def model_result_from_payload(
    payload: object,
    *,
    expected_attribute_ids: tuple[str, ...],
    allowed_evidence_ids: frozenset[str],
) -> ContextResolverModelResult:
    """Parse a complete exact-set response and validate evidence semantics."""

    top_level = _mapping(payload, name="payload")
    _require_exact_keys(top_level, expected=_TOP_LEVEL_KEYS)
    results = _mapping(top_level["results"], name="results")
    _require_exact_keys(results, expected=frozenset(expected_attribute_ids))

    attributes = tuple(
        _model_attribute(
            external_id,
            results[external_id],
            allowed_evidence_ids=allowed_evidence_ids,
        )
        for external_id in expected_attribute_ids
    )
    return ContextResolverModelResult(attributes=attributes)


def _model_attribute(
    external_id: str,
    value: object,
    *,
    allowed_evidence_ids: frozenset[str],
) -> ContextResolverModelAttribute:
    result = _mapping(value, name="attribute")
    _require_exact_keys(result, expected=_RESULT_KEYS)
    resolution = _status(result["resolution"])
    attribute_value = _optional_string(result["value"], max_length=_MAX_VALUE_CHARS)
    confidence = _confidence(result["confidence"])
    evidence_ids = _evidence_ids(
        result["evidence_ids"],
        allowed_evidence_ids=allowed_evidence_ids,
    )
    _validate_resolution(
        resolution=resolution,
        value=attribute_value,
        confidence=confidence,
        evidence_ids=evidence_ids,
    )
    return ContextResolverModelAttribute(
        attribute_external_id=external_id,
        value=attribute_value,
        confidence_score=confidence,
        status=resolution,
        evidence_ids=evidence_ids,
    )


def _evidence_ids(
    value: object,
    *,
    allowed_evidence_ids: frozenset[str],
) -> tuple[str, ...]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise TypeError("evidence_ids must be an array")
    values = cast(Sequence[object], value)
    result = tuple(_string(item) for item in values)
    if len(set(result)) != len(result):
        raise ValueError("duplicate evidence id")
    if any(evidence_id not in allowed_evidence_ids for evidence_id in result):
        raise ValueError("unknown evidence id")
    return result[:_MAX_EVIDENCE_COUNT]


def _validate_resolution(
    *,
    resolution: ResolvedAttributeStatus,
    value: str | None,
    confidence: float | None,
    evidence_ids: tuple[str, ...],
) -> None:
    if resolution == ResolvedAttributeStatus.MISSING:
        if value is not None or confidence is not None or evidence_ids:
            raise ValueError("missing result has incompatible fields")
        return
    if value is None or not evidence_ids:
        raise ValueError("resolved result requires value and evidence")


def _mapping(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be an object")
    mapping = cast(Mapping[object, object], value)
    if any(not isinstance(key, str) for key in mapping):
        raise TypeError(f"{name} keys must be strings")
    return cast(Mapping[str, object], mapping)


def _require_exact_keys(value: Mapping[str, object], *, expected: frozenset[str]) -> None:
    if set(value) != set(expected):
        raise ValueError("response keys do not match the expected contract")


def _status(value: object) -> ResolvedAttributeStatus:
    if not isinstance(value, str):
        raise TypeError("resolution must be a string")
    try:
        return ResolvedAttributeStatus(value)
    except ValueError as exc:
        raise ValueError("unsupported resolution") from exc


def _optional_string(value: object, *, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("value must be a string")
    stripped = value.strip()
    if not stripped or len(stripped) > max_length:
        raise ValueError("value is empty or exceeds the safe limit")
    return stripped


def _string(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError("value must be a non-empty string")
    return value.strip()


def _confidence(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError("confidence must be a number")
    result = float(value)
    if not math.isfinite(result) or result < 0 or result > 1:
        raise ValueError("confidence must be between zero and one")
    return round(result, 6)
