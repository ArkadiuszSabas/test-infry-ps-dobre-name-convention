"""Typed helpers for inspecting JSON-like OCR pipeline config values."""

from collections.abc import Mapping, Sequence
from typing import cast


def schema_mapping(value: object) -> Mapping[str, object] | None:
    """Return a schema mapping when the value has object shape."""

    if not isinstance(value, Mapping):
        return None
    return cast(Mapping[str, object], value)


def object_mapping(value: object) -> Mapping[object, object] | None:
    """Return a generic object-key mapping when the value has object shape."""

    if not isinstance(value, Mapping):
        return None
    return cast(Mapping[object, object], value)


def object_sequence(value: object) -> Sequence[object] | None:
    """Return a sequence when the value has JSON array shape."""

    if not isinstance(value, list | tuple):
        return None
    return cast(Sequence[object], value)
