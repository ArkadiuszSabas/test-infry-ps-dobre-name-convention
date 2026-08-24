"""System catalog extension value query helpers."""

from uuid import UUID

from sqlalchemy import outerjoin, select
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.domain.document_types.models import DocumentType
from docmind_api.infrastructure.persistence.dictionaries.tables import dictionary_entries_table
from docmind_api.infrastructure.persistence.system_catalogs.read_models import StoredExtensionValue
from docmind_api.infrastructure.persistence.system_catalogs.tables import (
    document_type_extension_values_table,
)


async def document_type_values(
    session: AsyncSession,
    document_types: tuple[DocumentType, ...],
) -> dict[UUID, dict[UUID, StoredExtensionValue]]:
    """Return stored extension values keyed by document type and field id."""

    document_type_ids = tuple(UUID(str(document_type.id)) for document_type in document_types)
    value_join = outerjoin(
        document_type_extension_values_table,
        dictionary_entries_table,
        document_type_extension_values_table.c.dictionary_entry_id == dictionary_entries_table.c.id,
    )
    statement = (
        select(
            document_type_extension_values_table.c.document_type_id,
            document_type_extension_values_table.c.extension_field_id,
            document_type_extension_values_table.c.dictionary_entry_id,
            document_type_extension_values_table.c.text_value,
            dictionary_entries_table.c.label.label("dictionary_entry_label"),
        )
        .select_from(value_join)
        .where(document_type_extension_values_table.c.document_type_id.in_(document_type_ids))
    )
    result = await session.execute(statement)
    values: dict[UUID, dict[UUID, StoredExtensionValue]] = {}
    for row in result.mappings():
        document_type_id = UUID(str(row["document_type_id"]))
        field_id = UUID(str(row["extension_field_id"]))
        values.setdefault(document_type_id, {})[field_id] = StoredExtensionValue(
            dictionary_entry_id=row["dictionary_entry_id"],
            text_value=row["text_value"],
            display_value=row["dictionary_entry_label"] or row["text_value"],
        )
    return values
