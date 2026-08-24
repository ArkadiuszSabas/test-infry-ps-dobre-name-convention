"""Document metadata schema and validation."""

from collections.abc import Mapping
from types import MappingProxyType

from docmind_api.domain.attributes.models import (
    AttributeValueSource,
    normalize_attribute_external_id,
)
from docmind_api.domain.documents.metadata_errors import (
    DocumentMetadataValidationError,
    InvalidMetadataConstraint,
    InvalidMetadataEnumValue,
    InvalidMetadataType,
    MissingRequiredMetadataField,
)
from docmind_api.domain.documents.metadata_scalar import (
    JsonScalar,
    metadata_value_diagnostics,
)
from docmind_api.domain.documents.metadata_schema import (
    DocumentMetadataSchema,
    MetadataFieldDefinition,
)
from docmind_api.domain.documents.metadata_value_validation import (
    is_missing_required_value,
    validate_field_constraints,
    validate_field_type,
)

__all__ = [
    "DocumentMetadataSchema",
    "DocumentMetadataValidationError",
    "InvalidMetadataConstraint",
    "InvalidMetadataEnumValue",
    "InvalidMetadataType",
    "JsonScalar",
    "MetadataFieldDefinition",
    "validate_document_metadata",
]


def validate_document_metadata(
    *,
    schema: DocumentMetadataSchema,
    values: Mapping[str, object],
) -> Mapping[str, JsonScalar]:
    """Validate metadata values against a document type schema and return normalized values."""

    fields_by_id = schema.fields_by_id
    normalized_values: dict[str, JsonScalar] = {}
    unknown_fields: list[str] = []
    invalid_types: list[InvalidMetadataType] = []
    invalid_enum_values: list[InvalidMetadataEnumValue] = []
    constraint_violations: list[InvalidMetadataConstraint] = []

    for raw_key, raw_value in values.items():
        try:
            key = normalize_attribute_external_id(raw_key)
        except ValueError:
            unknown_fields.append(raw_key)
            continue

        field = fields_by_id.get(key)
        if field is None:
            unknown_fields.append(key)
            continue

        typed_value, type_issue = validate_field_type(field=field, value=raw_value)
        if type_issue is not None:
            invalid_types.append(type_issue)
            continue

        value = typed_value
        if field.value_source == AttributeValueSource.DICTIONARY:
            allowed_values = field.dictionary_entry_external_ids
            should_validate_allowed_values = bool(allowed_values)
        else:
            allowed_values = field.allowed_values
            should_validate_allowed_values = bool(allowed_values)

        if should_validate_allowed_values and value not in allowed_values:
            invalid_enum_values.append(
                InvalidMetadataEnumValue(
                    field=key,
                    allowed_values=allowed_values,
                    actual=metadata_value_diagnostics(value),
                ),
            )
            continue

        constraint_violations.extend(
            validate_field_constraints(field=field, value=value),
        )
        normalized_values[key] = value

    missing_required_fields = tuple(
        MissingRequiredMetadataField(
            id=str(field.attribute_definition_id),
            name=field.name,
        )
        for field in sorted(schema.fields, key=lambda field: field.attribute_id)
        if field.required
        and is_missing_required_value(
            normalized_values.get(field.attribute_id),
        )
    )
    if (
        unknown_fields
        or missing_required_fields
        or invalid_types
        or invalid_enum_values
        or constraint_violations
    ):
        raise DocumentMetadataValidationError(
            document_type_id=schema.document_type_id,
            unknown_fields=tuple(sorted(unknown_fields)),
            missing_required_fields=missing_required_fields,
            invalid_types=tuple(invalid_types),
            invalid_enum_values=tuple(invalid_enum_values),
            constraint_violations=tuple(constraint_violations),
        )

    return MappingProxyType(normalized_values)
