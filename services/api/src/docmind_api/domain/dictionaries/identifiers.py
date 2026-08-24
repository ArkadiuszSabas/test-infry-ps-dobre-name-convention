"""Custom dictionary identifier validation."""

from docmind_api.domain.dictionaries.constants import DICTIONARY_ID_MAX_LENGTH


def normalize_dictionary_external_id(value: str) -> str:
    """Validate and return a stable dictionary-scoped external identifier."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("Dictionary external_id cannot be empty.")
    if len(normalized) > DICTIONARY_ID_MAX_LENGTH:
        raise ValueError(
            f"Dictionary external_id cannot exceed {DICTIONARY_ID_MAX_LENGTH} characters.",
        )

    return normalized
