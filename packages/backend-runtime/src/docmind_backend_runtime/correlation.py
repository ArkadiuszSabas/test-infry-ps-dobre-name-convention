"""Correlation id parsing and generation."""

from collections.abc import Mapping
from uuid import uuid4

MAX_CORRELATION_ID_LENGTH = 128
CORRELATION_ID_HEADER = "x-correlation-id"


def generate_correlation_id() -> str:
    """Generate a compact correlation id for requests without one."""

    return uuid4().hex


def get_or_create_correlation_id(
    headers: Mapping[str, str],
    *,
    header_name: str = CORRELATION_ID_HEADER,
) -> str:
    """Read a safe correlation id from headers or generate a new one."""

    header_value = headers.get(header_name, "")
    candidate = header_value.strip()

    if _is_safe_correlation_id(candidate):
        return candidate

    return generate_correlation_id()


def _is_safe_correlation_id(value: str) -> bool:
    if not value or len(value) > MAX_CORRELATION_ID_LENGTH:
        return False

    return all(_is_safe_correlation_id_character(character) for character in value)


def _is_safe_correlation_id_character(character: str) -> bool:
    return character.isascii() and (character.isalnum() or character in {".", "-", "_", ":", "/"})
