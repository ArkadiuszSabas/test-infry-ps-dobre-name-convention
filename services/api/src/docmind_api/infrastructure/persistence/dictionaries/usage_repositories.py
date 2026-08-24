"""Custom dictionary usage repository implementations."""

from uuid import UUID

from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.dictionaries.ports import DictionaryUsageRepository
from docmind_api.domain.attributes.models import AttributeStatus
from docmind_api.domain.dictionaries.models import DictionaryEntryUsage, DictionaryUsage
from docmind_api.infrastructure.persistence.attributes.tables import (
    attribute_definitions_table,
)
from docmind_api.infrastructure.persistence.dictionaries.mappers import coerce_uuid
from docmind_api.infrastructure.persistence.dictionaries.tables import (
    dictionaries_table,
    dictionary_entries_table,
)
from docmind_api.infrastructure.persistence.documents.tables import documents_table
from docmind_api.infrastructure.persistence.system_catalogs.tables import (
    document_type_extension_values_table,
    system_catalog_extension_fields_table,
)


class SqlAlchemyDictionaryUsageRepository(DictionaryUsageRepository):
    """Dictionary dependency reader used by deletion and deactivation guards."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_usage(self, dictionary_id: UUID | str) -> DictionaryUsage:
        normalized_id = await _resolve_dictionary_id(self._session, dictionary_id)
        if normalized_id is None:
            return DictionaryUsage()
        attribute_bindings = await self._session.scalar(
            select(func.count(attribute_definitions_table.c.id)).where(
                attribute_definitions_table.c.dictionary_id == normalized_id,
            ),
        )
        active_attribute_bindings = await self._session.scalar(
            select(func.count(attribute_definitions_table.c.id)).where(
                attribute_definitions_table.c.dictionary_id == normalized_id,
                attribute_definitions_table.c.status == AttributeStatus.ACTIVE.value,
            ),
        )
        system_catalog_fields = await self._session.scalar(
            select(func.count(system_catalog_extension_fields_table.c.id)).where(
                system_catalog_extension_fields_table.c.dictionary_id == normalized_id,
            ),
        )
        active_system_catalog_fields = await self._session.scalar(
            select(func.count(system_catalog_extension_fields_table.c.id)).where(
                system_catalog_extension_fields_table.c.dictionary_id == normalized_id,
                system_catalog_extension_fields_table.c.is_active.is_(True),
            ),
        )
        entries = await self._session.scalar(
            select(func.count(dictionary_entries_table.c.id)).where(
                dictionary_entries_table.c.dictionary_id == normalized_id,
            ),
        )
        return DictionaryUsage(
            attribute_bindings=attribute_bindings or 0,
            active_attribute_bindings=active_attribute_bindings or 0,
            system_catalog_fields=system_catalog_fields or 0,
            active_system_catalog_fields=active_system_catalog_fields or 0,
            entries=entries or 0,
        )

    async def get_entry_usage(
        self,
        dictionary_id: UUID | str,
        entry_external_id: str,
    ) -> DictionaryEntryUsage:
        normalized_id = await _resolve_dictionary_id(self._session, dictionary_id)
        if normalized_id is None:
            return DictionaryEntryUsage()

        attribute_key = func.coalesce(
            attribute_definitions_table.c.external_id,
            cast(attribute_definitions_table.c.id, String),
        )
        referenced_documents = await self._session.scalar(
            select(func.count(func.distinct(documents_table.c.id)))
            .select_from(documents_table)
            .where(
                select(attribute_definitions_table.c.id)
                .where(
                    attribute_definitions_table.c.dictionary_id == normalized_id,
                    func.jsonb_extract_path_text(
                        documents_table.c.metadata_values,
                        attribute_key,
                    )
                    == entry_external_id,
                )
                .exists(),
            ),
        )
        document_type_extension_values = await self._session.scalar(
            select(func.count(document_type_extension_values_table.c.id)).where(
                document_type_extension_values_table.c.dictionary_entry_id
                == select(dictionary_entries_table.c.id)
                .where(
                    dictionary_entries_table.c.dictionary_id == normalized_id,
                    dictionary_entries_table.c.external_id == entry_external_id,
                )
                .scalar_subquery(),
            ),
        )
        return DictionaryEntryUsage(
            document_metadata_values=referenced_documents or 0,
            document_type_extension_values=document_type_extension_values or 0,
        )


async def _resolve_dictionary_id(session: AsyncSession, dictionary_id: UUID | str) -> UUID | None:
    normalized_id = coerce_uuid(dictionary_id)
    if normalized_id is not None:
        existing_id = await session.scalar(
            select(dictionaries_table.c.id).where(dictionaries_table.c.id == normalized_id),
        )
        if existing_id is not None:
            return existing_id
        return None
    statement = select(dictionaries_table.c.id).where(
        dictionaries_table.c.external_id == str(dictionary_id),
    )
    return await session.scalar(statement)
