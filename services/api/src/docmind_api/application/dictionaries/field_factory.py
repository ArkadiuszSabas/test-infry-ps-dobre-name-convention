"""Dictionary field construction helpers."""

from datetime import datetime
from uuid import uuid4

from docmind_api.application.dictionaries.commands import SaveDictionaryFieldItem
from docmind_api.application.dictionaries.ports import DictionaryFieldIdFactory
from docmind_api.domain.dictionaries.models import (
    Dictionary,
    DictionaryField,
    normalize_dictionary_external_id,
)


def build_dictionary_field(
    *,
    item: SaveDictionaryFieldItem,
    dictionary: Dictionary,
    existing_fields: dict[str, DictionaryField],
    timestamp: datetime,
    field_id_factory: DictionaryFieldIdFactory | None,
) -> DictionaryField:
    """Build a field while preserving identity for matching external IDs."""

    normalized_external_id = normalize_dictionary_external_id(item.external_id)
    existing_field = existing_fields.get(normalized_external_id)
    if existing_field is not None:
        field_id = existing_field.id
        created_at = existing_field.created_at
    else:
        field_id = field_id_factory.new_id() if field_id_factory is not None else uuid4()
        created_at = timestamp

    return DictionaryField(
        id=field_id,
        dictionary_id=dictionary.id,
        external_id=item.external_id,
        label=item.label,
        data_type=item.data_type,
        required=item.required,
        constraints=item.constraints,
        normalization=item.normalization,
        format=item.format,
        is_unique=item.is_unique,
        sort_order=item.sort_order,
        status=item.status,
        created_at=created_at,
        updated_at=timestamp,
    )
