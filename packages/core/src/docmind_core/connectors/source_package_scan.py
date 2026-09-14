"""Text matching helpers for source-package forbidden-term scans."""

from __future__ import annotations

import unicodedata

_TEXT_BYTES = frozenset(range(32, 127)) | {8, 9, 10, 12, 13}


def normalize_for_scan(value: str) -> str:
    """Normalize text for case- and accent-insensitive source scans."""

    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def normalized_terms(forbidden_terms: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    """Pair configured terms with their normalized scan values."""

    return tuple((term, normalize_for_scan(term)) for term in forbidden_terms if term)


def contains_forbidden_term(
    value: str,
    term: str,
    *,
    scan_short_aliases: bool = True,
) -> bool:
    """Match long terms as substrings and two-character aliases as complete tokens."""

    if not term:
        return False
    is_short_alias = len(term) <= 2 and term.isalnum()
    if not is_short_alias:
        return term in value
    if not scan_short_aliases:
        return False

    start = 0
    while (index := value.find(term, start)) >= 0:
        end = index + len(term)
        starts_at_boundary = index == 0 or not value[index - 1].isalnum()
        ends_at_boundary = end == len(value) or not value[end].isalnum()
        if starts_at_boundary and ends_at_boundary:
            return True
        start = index + 1
    return False


def is_probably_binary(content: bytes) -> bool:
    """Return whether the payload is unsuitable for short-alias text scans."""

    if not content:
        return False
    if b"\x00" in content:
        return True
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        pass
    else:
        return False

    sample = content[:8192]
    non_text_count = sum(byte not in _TEXT_BYTES for byte in sample)
    return non_text_count / len(sample) > 0.30
