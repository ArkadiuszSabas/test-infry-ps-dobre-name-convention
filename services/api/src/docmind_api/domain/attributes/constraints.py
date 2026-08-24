"""Attribute metadata constraint models and validation."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Self

from docmind_api.domain.attributes.constants import ATTRIBUTE_CONSTRAINT_PATTERN_MAX_LENGTH
from docmind_api.domain.attributes.enums import AttributeDataType


@dataclass(frozen=True, slots=True)
class AttributeConstraints:
    """Validation constraints attached to a metadata field definition."""

    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None

    def __post_init__(self) -> None:
        min_length = _normalize_optional_non_negative_int(
            self.min_length,
            field_name="min_length",
        )
        max_length = _normalize_optional_non_negative_int(
            self.max_length,
            field_name="max_length",
        )
        pattern = _normalize_optional_pattern(self.pattern)
        min_value = _normalize_optional_finite_number(
            self.min_value,
            field_name="min_value",
        )
        max_value = _normalize_optional_finite_number(
            self.max_value,
            field_name="max_value",
        )

        if min_length is not None and max_length is not None and min_length > max_length:
            raise ValueError("Attribute constraint min_length cannot exceed max_length.")
        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValueError("Attribute constraint min_value cannot exceed max_value.")

        object.__setattr__(self, "min_length", min_length)
        object.__setattr__(self, "max_length", max_length)
        object.__setattr__(self, "pattern", pattern)
        object.__setattr__(self, "min_value", min_value)
        object.__setattr__(self, "max_value", max_value)

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> Self:
        """Create constraints from persisted or API JSON fields."""

        supported_keys = {"min_length", "max_length", "pattern", "min_value", "max_value"}
        unknown_keys = tuple(sorted(set(values) - supported_keys))
        if unknown_keys:
            raise ValueError(
                f"Attribute constraints contain unsupported keys: {', '.join(unknown_keys)}.",
            )

        return cls(
            min_length=_optional_int_from_mapping(values, "min_length"),
            max_length=_optional_int_from_mapping(values, "max_length"),
            pattern=_optional_str_from_mapping(values, "pattern"),
            min_value=_optional_number_from_mapping(values, "min_value"),
            max_value=_optional_number_from_mapping(values, "max_value"),
        )

    def as_json(self) -> dict[str, int | float | str]:
        """Return the non-empty JSON representation for storage and API responses."""

        values: dict[str, int | float | str] = {}
        if self.min_length is not None:
            values["min_length"] = self.min_length
        if self.max_length is not None:
            values["max_length"] = self.max_length
        if self.pattern is not None:
            values["pattern"] = self.pattern
        if self.min_value is not None:
            values["min_value"] = self.min_value
        if self.max_value is not None:
            values["max_value"] = self.max_value

        return values

    def validate_for_data_type(self, data_type: AttributeDataType) -> None:
        """Ensure the configured constraints are meaningful for the data type."""

        has_text_constraints = any(
            value is not None for value in (self.min_length, self.max_length, self.pattern)
        )
        has_numeric_constraints = any(
            value is not None for value in (self.min_value, self.max_value)
        )
        if data_type in {AttributeDataType.STRING, AttributeDataType.IDENTIFIER}:
            if has_numeric_constraints:
                raise ValueError("String attributes cannot define numeric value constraints.")
            return

        if data_type in {AttributeDataType.INTEGER, AttributeDataType.NUMBER}:
            if has_text_constraints:
                raise ValueError(
                    "Numeric attributes cannot define text length or pattern constraints.",
                )
            return

        if data_type == AttributeDataType.LEGACY_SCALAR and (
            has_text_constraints or has_numeric_constraints
        ):
            raise ValueError("Legacy scalar attributes cannot define constraints.")

        if has_text_constraints or has_numeric_constraints:
            raise ValueError(
                f"{data_type.value} attributes do not support constraints yet.",
            )


def _normalize_optional_non_negative_int(value: object, *, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Attribute constraint {field_name} must be an integer.")
    if value < 0:
        raise ValueError(f"Attribute constraint {field_name} cannot be negative.")

    return value


def _normalize_optional_finite_number(
    value: object,
    *,
    field_name: str,
) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"Attribute constraint {field_name} must be a finite number.")
    if not isfinite(value):
        raise ValueError(f"Attribute constraint {field_name} must be a finite number.")

    return value


def _normalize_optional_pattern(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > ATTRIBUTE_CONSTRAINT_PATTERN_MAX_LENGTH:
        raise ValueError(
            "Attribute constraint pattern cannot exceed "
            f"{ATTRIBUTE_CONSTRAINT_PATTERN_MAX_LENGTH} characters.",
        )
    try:
        re.compile(normalized)
    except re.error as error:
        raise ValueError("Attribute constraint pattern must be a valid regex.") from error

    return normalized


def _optional_int_from_mapping(values: Mapping[str, object], key: str) -> int | None:
    value = values.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Attribute constraint {key} must be an integer.")

    return value


def _optional_number_from_mapping(values: Mapping[str, object], key: str) -> int | float | None:
    value = values.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"Attribute constraint {key} must be a finite number.")

    return value


def _optional_str_from_mapping(values: Mapping[str, object], key: str) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Attribute constraint {key} must be a string.")

    return value
