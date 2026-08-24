"""Application validation for dynamic document type extension values."""

from datetime import datetime
from uuid import UUID

from docmind_api.application.document_types.commands import DocumentTypeValidationError
from docmind_api.application.document_types.ports import (
    DocumentTypeExtensionValueIdFactory,
    DocumentTypeExtensionValueLookup,
    DocumentTypeExtensionValuePayload,
)
from docmind_api.domain.system_catalogs.models import (
    DocumentTypeExtensionValue,
    SystemCatalogExtensionField,
    SystemCatalogExtensionValueType,
    normalize_extension_text_value,
)


async def validated_document_type_values(
    *,
    value_id_factory: DocumentTypeExtensionValueIdFactory,
    lookup: DocumentTypeExtensionValueLookup,
    document_type_id: UUID,
    fields: tuple[SystemCatalogExtensionField, ...],
    values: tuple[DocumentTypeExtensionValuePayload, ...],
    timestamp: datetime,
) -> tuple[DocumentTypeExtensionValue, ...]:
    """Validate submitted extension values and return values ready for persistence."""

    fields_by_id = {UUID(str(field.id)): field for field in fields}
    submitted_field_ids: set[UUID] = set()
    stored_values: list[DocumentTypeExtensionValue] = []

    for payload in values:
        field_id = UUID(str(payload.extension_field_id))
        field = fields_by_id.get(field_id)
        if field is None:
            raise DocumentTypeValidationError(
                message="Document type extension value references an inactive or missing field.",
            )
        if field_id in submitted_field_ids:
            raise DocumentTypeValidationError(
                message="Document type extension values cannot repeat a field.",
            )
        submitted_field_ids.add(field_id)
        value = await _validated_value_for_field(
            value_id_factory=value_id_factory,
            lookup=lookup,
            document_type_id=document_type_id,
            field=field,
            payload=payload,
            timestamp=timestamp,
        )
        if value is not None:
            stored_values.append(value)

    stored_field_ids = {UUID(str(value.extension_field_id)) for value in stored_values}
    missing_required_fields = tuple(
        field.code
        for field in fields
        if field.is_required and UUID(str(field.id)) not in stored_field_ids
    )
    if missing_required_fields:
        raise DocumentTypeValidationError(
            message="Required document type extension values are missing.",
        )
    return tuple(stored_values)


async def _validated_value_for_field(
    *,
    value_id_factory: DocumentTypeExtensionValueIdFactory,
    lookup: DocumentTypeExtensionValueLookup,
    document_type_id: UUID,
    field: SystemCatalogExtensionField,
    payload: DocumentTypeExtensionValuePayload,
    timestamp: datetime,
) -> DocumentTypeExtensionValue | None:
    if field.value_type == SystemCatalogExtensionValueType.TEXT:
        return _text_value_for_field(
            value_id_factory=value_id_factory,
            document_type_id=document_type_id,
            field=field,
            payload=payload,
            timestamp=timestamp,
        )

    try:
        dictionary_text_value = normalize_extension_text_value(payload.text_value)
    except ValueError as error:
        raise DocumentTypeValidationError(message=str(error)) from error
    if dictionary_text_value is not None:
        raise DocumentTypeValidationError(
            message="Dictionary extension fields cannot store text_value.",
        )
    if payload.dictionary_entry_id is None:
        return None
    entry_id = UUID(str(payload.dictionary_entry_id))
    if not await lookup.active_dictionary_entry_belongs_to_active_dictionary(
        entry_id=entry_id,
        dictionary_id=UUID(str(field.dictionary_id)),
    ):
        raise DocumentTypeValidationError(
            message=(
                "Dictionary extension value must reference an active entry from the "
                "configured active dictionary."
            ),
        )
    return DocumentTypeExtensionValue(
        id=value_id_factory.new_id(),
        document_type_id=document_type_id,
        extension_field_id=field.id,
        dictionary_entry_id=entry_id,
        text_value=None,
        created_at=timestamp,
        updated_at=timestamp,
    )


def _text_value_for_field(
    *,
    value_id_factory: DocumentTypeExtensionValueIdFactory,
    document_type_id: UUID,
    field: SystemCatalogExtensionField,
    payload: DocumentTypeExtensionValuePayload,
    timestamp: datetime,
) -> DocumentTypeExtensionValue | None:
    if payload.dictionary_entry_id is not None:
        raise DocumentTypeValidationError(
            message="Text extension fields cannot store dictionary_entry_id.",
        )
    try:
        text_value = normalize_extension_text_value(payload.text_value)
    except ValueError as error:
        raise DocumentTypeValidationError(message=str(error)) from error
    if text_value is None:
        return None
    return DocumentTypeExtensionValue(
        id=value_id_factory.new_id(),
        document_type_id=document_type_id,
        extension_field_id=field.id,
        dictionary_entry_id=None,
        text_value=text_value,
        created_at=timestamp,
        updated_at=timestamp,
    )
