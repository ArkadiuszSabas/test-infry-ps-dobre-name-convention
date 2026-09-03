"""Content-free diagnostics for Context Resolver response validation failures."""

from __future__ import annotations

import json

_REASON_BY_MESSAGE = {
    "confidence must be between zero and one": "CONFIDENCE_OUT_OF_RANGE",
    "duplicate evidence id": "DUPLICATE_EVIDENCE_ID",
    "missing result has incompatible fields": "MISSING_FIELDS_INCOMPATIBLE",
    "resolved result requires value and evidence": "RESOLVED_FIELDS_INCOMPLETE",
    "response keys do not match the expected contract": "RESPONSE_KEYS_MISMATCH",
    "unknown evidence id": "UNKNOWN_EVIDENCE_ID",
    "unsupported resolution": "RESOLUTION_UNSUPPORTED",
    "value is empty or exceeds the safe limit": "VALUE_INVALID",
}


def model_output_validation_reason(error: Exception) -> str:
    """Map parser failures to an allowlisted reason without exposing model output."""

    if isinstance(error, json.JSONDecodeError):
        return "MALFORMED_JSON"
    return _REASON_BY_MESSAGE.get(str(error), "OUTPUT_CONTRACT_VIOLATION")
