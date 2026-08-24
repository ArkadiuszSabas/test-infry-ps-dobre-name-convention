"""Per-field document metadata value validation."""

from datetime import date, datetime
from math import isfinite
from re import fullmatch

from docmind_api.domain.attributes.models import AttributeDataType
from docmind_api.domain.documents.metadata_errors import (
    InvalidMetadataConstraint,
    InvalidMetadataType,
)
from docmind_api.domain.documents.metadata_scalar import (
    JsonScalar,
    cast_json_scalar,
    is_json_scalar,
    metadata_type_name,
    metadata_value_diagnostics,
)
from docmind_api.domain.documents.metadata_schema import MetadataFieldDefinition


def validate_field_type(
    *,
    field: MetadataFieldDefinition,
    value: object,
) -> tuple[JsonScalar, InvalidMetadataType | None]:
    """Validate and normalize a single metadata value by field type."""

    if value is None:
        return None, None
    if not is_json_scalar(value):
        return (
            None,
            InvalidMetadataType(
                field=field.attribute_id,
                expected=field.data_type.value,
                actual=metadata_type_name(value),
            ),
        )

    data_type = field.data_type
    if data_type == AttributeDataType.LEGACY_SCALAR:
        return cast_json_scalar(value), None
    if data_type in {AttributeDataType.STRING, AttributeDataType.IDENTIFIER}:
        if isinstance(value, str):
            return value, None
        return _invalid_type(field=field, expected=data_type.value, value=value)
    if data_type == AttributeDataType.INTEGER:
        if isinstance(value, int) and not isinstance(value, bool):
            return value, None
        return _invalid_type(field=field, expected=data_type.value, value=value)
    if data_type == AttributeDataType.NUMBER:
        if isinstance(value, int | float) and not isinstance(value, bool) and isfinite(value):
            return cast_json_scalar(value), None
        return _invalid_type(field=field, expected=data_type.value, value=value)
    if data_type == AttributeDataType.BOOLEAN:
        if isinstance(value, bool):
            return value, None
        return _invalid_type(field=field, expected=data_type.value, value=value)
    if data_type == AttributeDataType.DATE:
        if isinstance(value, str):
            normalized_date = _parse_iso_date(value)
            if normalized_date is not None:
                return normalized_date, None
        return _invalid_type(field=field, expected="iso_date", value=value)
    if data_type == AttributeDataType.DATETIME:
        if isinstance(value, str):
            normalized_datetime = _parse_iso_datetime(value)
            if normalized_datetime is not None:
                return normalized_datetime, None
        return _invalid_type(field=field, expected="iso_datetime", value=value)

    return _invalid_type(field=field, expected=data_type.value, value=value)


def validate_field_constraints(
    *,
    field: MetadataFieldDefinition,
    value: JsonScalar,
) -> tuple[InvalidMetadataConstraint, ...]:
    """Validate a single metadata value against configured constraints."""

    constraints = field.constraints
    violations: list[InvalidMetadataConstraint] = []
    if value is None:
        return ()

    if isinstance(value, str):
        if constraints.min_length is not None and len(value) < constraints.min_length:
            violations.append(
                InvalidMetadataConstraint(
                    field=field.attribute_id,
                    constraint="min_length",
                    expected=constraints.min_length,
                    expected_length=constraints.min_length,
                    actual=metadata_value_diagnostics(value),
                ),
            )
        if constraints.max_length is not None and len(value) > constraints.max_length:
            violations.append(
                InvalidMetadataConstraint(
                    field=field.attribute_id,
                    constraint="max_length",
                    expected=constraints.max_length,
                    expected_length=constraints.max_length,
                    actual=metadata_value_diagnostics(value),
                ),
            )
        if constraints.pattern is not None and fullmatch(constraints.pattern, value) is None:
            violations.append(
                InvalidMetadataConstraint(
                    field=field.attribute_id,
                    constraint="pattern",
                    expected=constraints.pattern,
                    actual=metadata_value_diagnostics(value),
                ),
            )

    if (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and field.data_type in {AttributeDataType.INTEGER, AttributeDataType.NUMBER}
    ):
        if constraints.min_value is not None and value < constraints.min_value:
            violations.append(
                InvalidMetadataConstraint(
                    field=field.attribute_id,
                    constraint="min_value",
                    expected=constraints.min_value,
                    actual=metadata_value_diagnostics(value),
                ),
            )
        if constraints.max_value is not None and value > constraints.max_value:
            violations.append(
                InvalidMetadataConstraint(
                    field=field.attribute_id,
                    constraint="max_value",
                    expected=constraints.max_value,
                    actual=metadata_value_diagnostics(value),
                ),
            )

    return tuple(violations)


def is_missing_required_value(value: object) -> bool:
    """Return whether a stored value should count as missing for a required field."""

    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True

    return False


def _invalid_type(
    *,
    field: MetadataFieldDefinition,
    expected: str,
    value: object,
) -> tuple[None, InvalidMetadataType]:
    return (
        None,
        InvalidMetadataType(
            field=field.attribute_id,
            expected=expected,
            actual=metadata_type_name(value),
        ),
    )


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
