"""Typed validation for dictionary entry values."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from re import fullmatch
from uuid import UUID

from docmind_api.domain.attributes.models import AttributeDataType
from docmind_api.domain.dictionaries.entries import DictionaryEntry, DictionaryEntryScalar
from docmind_api.domain.dictionaries.fields import DictionaryField


@dataclass(frozen=True, slots=True)
class DictionaryEntryValuesValidationError(ValueError):
    """Raised when a dictionary entry values object does not match field schema."""

    unknown_fields: tuple[str, ...] = ()
    missing_required_fields: tuple[str, ...] = ()
    invalid_types: tuple[dict[str, str], ...] = ()
    constraint_violations: tuple[dict[str, object], ...] = ()
    duplicate_unique_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        ValueError.__init__(self, "Dictionary entry values do not match field schema.")

    def as_details(self) -> dict[str, object]:
        """Return API-safe validation diagnostics."""

        return {
            "unknown_fields": self.unknown_fields,
            "missing_required_fields": self.missing_required_fields,
            "invalid_types": self.invalid_types,
            "constraint_violations": self.constraint_violations,
            "duplicate_unique_fields": self.duplicate_unique_fields,
        }


def validate_dictionary_entry_values(
    *,
    fields: tuple[DictionaryField, ...],
    values: Mapping[str, object],
    existing_entries: tuple[DictionaryEntry, ...] = (),
    current_entry_id: UUID | None = None,
) -> Mapping[str, DictionaryEntryScalar]:
    """Validate and normalize entry values against active dictionary fields."""

    active_fields = tuple(field for field in fields if field.is_active)
    fields_by_id = {field.external_id: field for field in active_fields}
    normalized_values: dict[str, DictionaryEntryScalar] = {}
    unknown_fields: list[str] = []
    invalid_types: list[dict[str, str]] = []
    constraint_violations: list[dict[str, object]] = []

    for key, raw_value in values.items():
        field = fields_by_id.get(key.strip())
        if field is None:
            unknown_fields.append(str(key))
            continue

        typed_value, invalid_type = _normalize_field_value(field=field, value=raw_value)
        if invalid_type is not None:
            invalid_types.append(invalid_type)
            continue

        normalized_value = _apply_string_normalization(field=field, value=typed_value)
        constraint_violations.extend(
            _validate_constraints(field=field, value=normalized_value),
        )
        normalized_values[field.external_id] = normalized_value

    missing_required_fields = tuple(
        sorted(
            field.external_id
            for field in active_fields
            if field.required and _is_missing(normalized_values.get(field.external_id))
        ),
    )
    duplicate_unique_fields = _duplicate_unique_fields(
        fields=active_fields,
        values=normalized_values,
        existing_entries=existing_entries,
        current_entry_id=current_entry_id,
    )
    if (
        unknown_fields
        or missing_required_fields
        or invalid_types
        or constraint_violations
        or duplicate_unique_fields
    ):
        raise DictionaryEntryValuesValidationError(
            unknown_fields=tuple(sorted(unknown_fields)),
            missing_required_fields=missing_required_fields,
            invalid_types=tuple(invalid_types),
            constraint_violations=tuple(constraint_violations),
            duplicate_unique_fields=duplicate_unique_fields,
        )

    return normalized_values


def _normalize_field_value(
    *,
    field: DictionaryField,
    value: object,
) -> tuple[DictionaryEntryScalar, dict[str, str] | None]:
    if value is None:
        return None, None
    data_type = field.data_type
    if data_type == AttributeDataType.STRING:
        if isinstance(value, str):
            return value, None
        return None, _invalid_type(field=field, expected="string", value=value)
    if data_type == AttributeDataType.INTEGER:
        if isinstance(value, int) and not isinstance(value, bool):
            return value, None
        return None, _invalid_type(field=field, expected="integer", value=value)
    if data_type == AttributeDataType.NUMBER:
        if isinstance(value, int | float) and not isinstance(value, bool) and isfinite(value):
            return value, None
        return None, _invalid_type(field=field, expected="number", value=value)
    if data_type == AttributeDataType.BOOLEAN:
        if isinstance(value, bool):
            return value, None
        return None, _invalid_type(field=field, expected="boolean", value=value)
    if data_type == AttributeDataType.DATE and isinstance(value, str):
        normalized_date = _parse_iso_date(value)
        if normalized_date is not None:
            return normalized_date, None
    if data_type == AttributeDataType.DATE:
        return None, _invalid_type(field=field, expected="iso_date", value=value)
    if data_type == AttributeDataType.DATETIME and isinstance(value, str):
        normalized_datetime = _parse_iso_datetime(value)
        if normalized_datetime is not None:
            return normalized_datetime, None
    if data_type == AttributeDataType.DATETIME:
        return None, _invalid_type(field=field, expected="iso_datetime", value=value)

    return None, _invalid_type(field=field, expected=data_type.value, value=value)


def _apply_string_normalization(
    *,
    field: DictionaryField,
    value: DictionaryEntryScalar,
) -> DictionaryEntryScalar:
    if not isinstance(value, str):
        return value

    normalized = value
    if field.normalization.get("trim") is True:
        normalized = normalized.strip()
    case = field.normalization.get("case")
    if case == "lower":
        normalized = normalized.lower()
    if case == "upper":
        normalized = normalized.upper()

    return normalized


def _validate_constraints(
    *,
    field: DictionaryField,
    value: DictionaryEntryScalar,
) -> tuple[dict[str, object], ...]:
    constraints = field.constraints
    violations: list[dict[str, object]] = []
    if value is None:
        return ()
    if isinstance(value, str):
        if constraints.min_length is not None and len(value) < constraints.min_length:
            violations.append(_constraint(field, "min_length", constraints.min_length))
        if constraints.max_length is not None and len(value) > constraints.max_length:
            violations.append(_constraint(field, "max_length", constraints.max_length))
        if constraints.pattern is not None and fullmatch(constraints.pattern, value) is None:
            violations.append(_constraint(field, "pattern", constraints.pattern))
    if isinstance(value, int | float) and not isinstance(value, bool):
        if constraints.min_value is not None and value < constraints.min_value:
            violations.append(_constraint(field, "min_value", constraints.min_value))
        if constraints.max_value is not None and value > constraints.max_value:
            violations.append(_constraint(field, "max_value", constraints.max_value))

    return tuple(violations)


def _duplicate_unique_fields(
    *,
    fields: tuple[DictionaryField, ...],
    values: Mapping[str, DictionaryEntryScalar],
    existing_entries: tuple[DictionaryEntry, ...],
    current_entry_id: UUID | None,
) -> tuple[str, ...]:
    duplicate_fields: set[str] = set()
    unique_fields = tuple(field for field in fields if field.is_unique)
    for field in unique_fields:
        if field.external_id not in values or values[field.external_id] is None:
            continue
        for entry in existing_entries:
            if current_entry_id is not None and UUID(str(entry.id)) == current_entry_id:
                continue
            existing_value = _normalized_existing_unique_value(
                field=field,
                values=entry.values,
            )
            if existing_value == values[field.external_id]:
                duplicate_fields.add(field.external_id)

    return tuple(sorted(duplicate_fields))


def _normalized_existing_unique_value(
    *,
    field: DictionaryField,
    values: Mapping[str, DictionaryEntryScalar],
) -> DictionaryEntryScalar:
    typed_value, invalid_type = _normalize_field_value(
        field=field,
        value=values.get(field.external_id),
    )
    if invalid_type is not None:
        return None
    return _apply_string_normalization(field=field, value=typed_value)


def _constraint(field: DictionaryField, constraint: str, expected: object) -> dict[str, object]:
    return {
        "field": field.external_id,
        "constraint": constraint,
        "expected": expected,
        "code": "DICTIONARY_FIELD_CONSTRAINT_FAILED",
    }


def _invalid_type(
    *,
    field: DictionaryField,
    expected: str,
    value: object,
) -> dict[str, str]:
    return {"field": field.external_id, "expected": expected, "actual": _type_name(value)}


def _type_name(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _parse_iso_date(value: str) -> str | None:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None

    return parsed.isoformat()


def _parse_iso_datetime(value: str) -> str | None:
    if "T" not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    return parsed.isoformat()
