"""Attribute identifier validation."""

from docmind_api.domain.attributes.constants import ATTRIBUTE_ID_MAX_LENGTH


def normalize_attribute_external_id(value: str) -> str:
    """Validate and return a stable optional attribute external identifier."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("Attribute external_id cannot be empty.")
    if len(normalized) > ATTRIBUTE_ID_MAX_LENGTH:
        raise ValueError(
            f"Attribute external_id cannot exceed {ATTRIBUTE_ID_MAX_LENGTH} characters.",
        )

    return normalized
