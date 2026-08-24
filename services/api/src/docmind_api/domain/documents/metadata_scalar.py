"""JSON scalar helpers for document metadata validation."""

from math import isfinite

type JsonScalar = str | int | float | bool | None


def is_json_scalar(value: object) -> bool:
    """Return whether a value can be stored as a finite JSON scalar."""

    if isinstance(value, bool):
        return True
    if isinstance(value, float):
        return isfinite(value)

    return value is None or isinstance(value, str | int)


def cast_json_scalar(value: object) -> JsonScalar:
    """Return a value as a JSON scalar after validation."""

    if value is None or isinstance(value, str | int | bool):
        return value
    if isinstance(value, float) and isfinite(value):
        return value

    raise TypeError("Expected a JSON scalar value.")


def metadata_type_name(value: object) -> str:
    """Return an API-safe type name for metadata validation details."""

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, float) and not isfinite(value):
        return "non_finite_number"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"

    return type(value).__name__


def metadata_value_diagnostics(value: object) -> dict[str, object]:
    """Return non-sensitive diagnostics for a submitted metadata value."""

    diagnostics: dict[str, object] = {"type": metadata_type_name(value)}
    if isinstance(value, str):
        diagnostics["length"] = len(value)

    return diagnostics
