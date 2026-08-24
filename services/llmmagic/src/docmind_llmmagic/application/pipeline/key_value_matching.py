"""Shared deterministic matching for OCR key-value labels."""

import unicodedata


def normalize_key_value_label(value: str) -> str:
    """Normalize Unicode alphanumeric label tokens for exact matching."""

    tokens: list[str] = []
    current: list[str] = []
    for character in unicodedata.normalize("NFKC", value).casefold():
        if character.isalnum():
            current.append(character)
            continue
        if current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return " ".join(tokens)
