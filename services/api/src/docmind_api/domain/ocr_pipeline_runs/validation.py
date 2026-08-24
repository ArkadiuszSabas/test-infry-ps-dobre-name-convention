"""Validation helpers for OCR pipeline run domain models."""


def normalize_required_text(name: str, value: str, *, max_length: int) -> str:
    """Return normalized required text or raise a domain validation error."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"OCR pipeline {name} is required.")
    if len(normalized) > max_length:
        raise ValueError(f"OCR pipeline {name} cannot exceed {max_length} characters.")
    return normalized


def normalize_optional_text(
    value: str | None,
    *,
    field_name: str,
    max_length: int,
) -> str | None:
    """Return normalized optional text or none for blank values."""

    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise ValueError(f"OCR pipeline {field_name} cannot exceed {max_length} characters.")
    return normalized
