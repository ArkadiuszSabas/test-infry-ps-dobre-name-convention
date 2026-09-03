"""Canonical fragment comparison for independently grounded aggregate values."""

import re
import unicodedata

_AGGREGATE_SEPARATOR = re.compile(r"(?:\r?\n+|[;•·]+\s*|(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ]))")
_LIST_PREFIX = re.compile(r"^\s*(?:[-*\u2013\u2014]|\d+[.)])\s*")
_EDGE_PUNCTUATION = re.compile(r"^\W+|\W+$", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")


def aggregate_fragments(value: str) -> tuple[str, ...]:
    """Split one validated aggregate using the same boundaries used for grounding."""

    return tuple(
        cleaned
        for item in _AGGREGATE_SEPARATOR.split(value)
        if (cleaned := _LIST_PREFIX.sub("", item).strip())
    )


def aggregate_values_equivalent(first: str, second: str) -> bool:
    """Compare grounded aggregate fragments without making their order significant."""

    first_signature = _aggregate_signature(first)
    return bool(first_signature) and first_signature == _aggregate_signature(second)


def _aggregate_signature(value: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            normalized
            for fragment in aggregate_fragments(value)
            if (normalized := _normalized_fragment(fragment))
        )
    )


def _normalized_fragment(value: str) -> str:
    normalized = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip().casefold()
    return _EDGE_PUNCTUATION.sub("", normalized)
