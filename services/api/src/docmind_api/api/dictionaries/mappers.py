"""HTTP response mappers for custom dictionary endpoints."""

from uuid import UUID

from docmind_api.api.dictionaries.schemas import (
    DictionaryEntryListEnvelope,
    DictionaryEntryListMeta,
    DictionaryEntryListSchema,
    DictionaryEntrySchema,
    DictionaryFieldSchema,
    DictionaryFieldsEnvelope,
    DictionaryFieldsMeta,
    DictionaryFieldsPayload,
    DictionarySchema,
)
from docmind_api.application.dictionaries.commands import DictionaryEntryPage
from docmind_api.domain.dictionaries.models import Dictionary, DictionaryEntry, DictionaryField


def to_dictionary_schema(dictionary: Dictionary) -> DictionarySchema:
    """Convert a dictionary domain object to its HTTP schema."""

    return DictionarySchema(
        id=UUID(str(dictionary.id)),
        external_id=dictionary.external_id,
        name=dictionary.name,
        description=dictionary.description,
        status=dictionary.status,
        schema_version=dictionary.schema_version,
        entries_version=dictionary.entries_version,
        created_at=dictionary.created_at,
        updated_at=dictionary.updated_at,
    )


def to_field_schema(field: DictionaryField) -> DictionaryFieldSchema:
    """Convert a dictionary field domain object to its HTTP schema."""

    if field.created_at is None or field.updated_at is None:
        raise ValueError("Persisted dictionary fields require audit timestamps.")

    return DictionaryFieldSchema(
        id=UUID(str(field.id)),
        dictionary_id=UUID(str(field.dictionary_id)),
        external_id=field.external_id,
        label=field.label,
        data_type=field.data_type,
        required=field.required,
        constraints=field.constraints.as_json(),
        normalization=dict(field.normalization),
        format=dict(field.format),
        is_unique=field.is_unique,
        sort_order=field.sort_order,
        status=field.status,
        created_at=field.created_at,
        updated_at=field.updated_at,
    )


def to_fields_envelope(
    *,
    dictionary_id: UUID,
    fields: tuple[DictionaryField, ...],
) -> DictionaryFieldsEnvelope:
    """Convert field schema rows to the standard HTTP envelope."""

    return DictionaryFieldsEnvelope(
        data=DictionaryFieldsPayload(fields=[to_field_schema(field) for field in fields]),
        meta=DictionaryFieldsMeta(dictionary_id=dictionary_id, field_count=len(fields)),
    )


def to_entry_schema(entry: DictionaryEntry) -> DictionaryEntrySchema:
    """Convert a dictionary entry domain object to its HTTP schema."""

    return DictionaryEntrySchema(
        id=UUID(str(entry.id)),
        dictionary_id=UUID(str(entry.dictionary_id)),
        external_id=entry.external_id,
        label=entry.label,
        values=dict(entry.values),
        status=entry.status,
        sort_order=entry.sort_order,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def to_entry_list_envelope(
    *,
    dictionary_id: UUID,
    page: DictionaryEntryPage,
) -> DictionaryEntryListEnvelope:
    """Convert a paged entry result to the standard HTTP envelope."""

    return DictionaryEntryListEnvelope(
        data=DictionaryEntryListSchema(
            entries=[to_entry_schema(entry) for entry in page.entries],
        ),
        meta=DictionaryEntryListMeta(
            dictionary_id=dictionary_id,
            returned_count=page.returned_count,
            total_count=page.total_count,
            limit=page.limit,
            offset=page.offset,
            has_more=page.has_more,
        ),
    )
