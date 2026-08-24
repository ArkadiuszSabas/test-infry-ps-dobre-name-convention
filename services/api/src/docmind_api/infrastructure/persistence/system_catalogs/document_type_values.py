"""Document type extension value persistence for system catalogs."""

from uuid import UUID

from sqlalchemy import delete, exists, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.document_types.ports import (
    DocumentTypeExtensionValueRepository,
    DocumentTypeReadModel,
)
from docmind_api.domain.document_types.models import DocumentType
from docmind_api.domain.system_catalogs.models import (
    DOCUMENT_TYPE_SYSTEM_CATALOG_KEY,
    DocumentTypeExtensionValue,
    SystemCatalogDisplayMode,
    SystemCatalogDisplayModePart,
    SystemCatalogExtensionField,
)
from docmind_api.infrastructure.persistence.dictionaries.tables import (
    dictionaries_table,
    dictionary_entries_table,
)
from docmind_api.infrastructure.persistence.system_catalogs.mappers import (
    display_mode_from_row,
    display_mode_part_from_row,
    field_from_row,
)
from docmind_api.infrastructure.persistence.system_catalogs.read_models import (
    build_document_type_read_model,
)
from docmind_api.infrastructure.persistence.system_catalogs.tables import (
    document_type_extension_values_table,
    system_catalog_display_mode_parts_table,
    system_catalog_display_modes_table,
    system_catalog_extension_fields_table,
)
from docmind_api.infrastructure.persistence.system_catalogs.value_queries import (
    document_type_values,
)


class SqlAlchemyDocumentTypeExtensionValueRepository(DocumentTypeExtensionValueRepository):
    """PostgreSQL-backed document type extension value repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_extension_fields(
        self,
        system_catalog_key: str,
    ) -> tuple[SystemCatalogExtensionField, ...]:
        """Return active extension fields for a system catalog."""

        return await self._list_fields(system_catalog_key, active_only=True)

    async def active_dictionary_entry_belongs_to_active_dictionary(
        self,
        *,
        entry_id: UUID,
        dictionary_id: UUID,
    ) -> bool:
        """Return whether an active entry belongs to the active configured dictionary."""

        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        dictionary_entries_table.c.id == entry_id,
                        dictionary_entries_table.c.dictionary_id == dictionary_id,
                        dictionary_entries_table.c.status == "active",
                        dictionaries_table.c.id == dictionary_entries_table.c.dictionary_id,
                        dictionaries_table.c.id == dictionary_id,
                        dictionaries_table.c.status == "active",
                    ),
                ),
            ),
        )

    async def replace_values(
        self,
        *,
        document_type_id: UUID,
        values: tuple[DocumentTypeExtensionValue, ...],
    ) -> None:
        """Replace active dynamic extension values for one document type."""

        active_field_ids_for_key = select(system_catalog_extension_fields_table.c.id).where(
            system_catalog_extension_fields_table.c.system_catalog_key
            == DOCUMENT_TYPE_SYSTEM_CATALOG_KEY,
            system_catalog_extension_fields_table.c.is_active.is_(True),
        )
        await self._session.execute(
            delete(document_type_extension_values_table).where(
                document_type_extension_values_table.c.document_type_id == document_type_id,
                document_type_extension_values_table.c.extension_field_id.in_(
                    active_field_ids_for_key,
                ),
            ),
        )
        for value in values:
            await self._session.execute(
                postgresql_insert(document_type_extension_values_table).values(
                    id=value.id,
                    document_type_id=value.document_type_id,
                    extension_field_id=value.extension_field_id,
                    dictionary_entry_id=value.dictionary_entry_id,
                    text_value=value.text_value,
                    created_at=value.created_at,
                    updated_at=value.updated_at,
                ),
            )

    async def build_read_models(
        self,
        document_types: tuple[DocumentType, ...],
    ) -> tuple[DocumentTypeReadModel, ...]:
        """Return document type read models sorted by the active default display mode."""

        if not document_types:
            return ()

        fields = await self._list_fields(DOCUMENT_TYPE_SYSTEM_CATALOG_KEY, active_only=True)
        values_by_document_type = await document_type_values(self._session, document_types)
        display_mode = await self._default_display_mode(DOCUMENT_TYPE_SYSTEM_CATALOG_KEY)
        read_models = tuple(
            build_document_type_read_model(
                document_type=document_type,
                fields=fields,
                values=values_by_document_type.get(UUID(str(document_type.id)), {}),
                display_mode=display_mode,
            )
            for document_type in document_types
        )
        return tuple(
            sorted(
                read_models,
                key=lambda item: (*item.sort_key, str(item.document_type.id)),
            ),
        )

    async def _list_fields(
        self,
        system_catalog_key: str,
        *,
        active_only: bool,
    ) -> tuple[SystemCatalogExtensionField, ...]:
        statement = select(system_catalog_extension_fields_table).where(
            system_catalog_extension_fields_table.c.system_catalog_key == system_catalog_key,
        )
        if active_only:
            statement = statement.where(system_catalog_extension_fields_table.c.is_active.is_(True))
        statement = statement.order_by(
            system_catalog_extension_fields_table.c.field_order.asc(),
            system_catalog_extension_fields_table.c.label.asc(),
            system_catalog_extension_fields_table.c.code.asc(),
        )
        result = await self._session.execute(statement)
        return tuple(field_from_row(row) for row in result.mappings())

    async def _list_display_modes(
        self,
        system_catalog_key: str,
    ) -> tuple[SystemCatalogDisplayMode, ...]:
        mode_statement = (
            select(system_catalog_display_modes_table)
            .where(system_catalog_display_modes_table.c.system_catalog_key == system_catalog_key)
            .order_by(
                system_catalog_display_modes_table.c.is_default.desc(),
                system_catalog_display_modes_table.c.name.asc(),
            )
        )
        mode_result = await self._session.execute(mode_statement)
        mode_rows = tuple(mode_result.mappings())
        if not mode_rows:
            return ()

        mode_ids = tuple(row["id"] for row in mode_rows)
        part_statement = (
            select(system_catalog_display_mode_parts_table)
            .where(system_catalog_display_mode_parts_table.c.display_mode_id.in_(mode_ids))
            .order_by(
                system_catalog_display_mode_parts_table.c.display_mode_id.asc(),
                system_catalog_display_mode_parts_table.c.part_order.asc(),
            )
        )
        part_result = await self._session.execute(part_statement)
        parts_by_mode_id: dict[UUID, list[SystemCatalogDisplayModePart]] = {}
        for row in part_result.mappings():
            part = display_mode_part_from_row(row)
            parts_by_mode_id.setdefault(UUID(str(part.display_mode_id)), []).append(part)

        return tuple(
            display_mode_from_row(
                row,
                parts=tuple(parts_by_mode_id.get(UUID(str(row["id"])), ())),
            )
            for row in mode_rows
        )

    async def _default_display_mode(
        self,
        system_catalog_key: str,
    ) -> SystemCatalogDisplayMode | None:
        display_modes = await self._list_display_modes(system_catalog_key)
        return next(
            (
                display_mode
                for display_mode in display_modes
                if display_mode.is_active and display_mode.is_default
            ),
            None,
        )
