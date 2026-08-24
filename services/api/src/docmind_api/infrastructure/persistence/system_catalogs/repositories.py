"""System catalog persistence repositories."""

from uuid import UUID

from sqlalchemy import delete, exists, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.system_catalogs.ports import SystemCatalogDefinitionRepository
from docmind_api.domain.document_types.models import DocumentTypeStatus
from docmind_api.domain.system_catalogs.models import (
    SystemCatalogDisplayMode,
    SystemCatalogDisplayModePart,
    SystemCatalogExtensionField,
)
from docmind_api.infrastructure.persistence.attributes.tables import attribute_definitions_table
from docmind_api.infrastructure.persistence.dictionaries.tables import dictionaries_table
from docmind_api.infrastructure.persistence.document_types.tables import document_types_table
from docmind_api.infrastructure.persistence.system_catalogs.mappers import (
    display_mode_from_row,
    display_mode_part_from_row,
    field_from_row,
)
from docmind_api.infrastructure.persistence.system_catalogs.tables import (
    document_type_extension_values_table,
    system_catalog_display_mode_parts_table,
    system_catalog_display_modes_table,
    system_catalog_extension_fields_table,
)


class SqlAlchemySystemCatalogRepository(SystemCatalogDefinitionRepository):
    """PostgreSQL-backed system catalog repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_definition(
        self,
        system_catalog_key: str,
    ) -> tuple[tuple[SystemCatalogExtensionField, ...], tuple[SystemCatalogDisplayMode, ...]]:
        """Return fields and display modes for one system catalog."""

        fields = await self._list_fields(system_catalog_key, active_only=False)
        display_modes = await self._list_display_modes(system_catalog_key)
        return fields, display_modes

    async def replace_definition(
        self,
        *,
        system_catalog_key: str,
        fields: tuple[SystemCatalogExtensionField, ...],
        display_modes: tuple[SystemCatalogDisplayMode, ...],
    ) -> tuple[tuple[SystemCatalogExtensionField, ...], tuple[SystemCatalogDisplayMode, ...]]:
        """Persist a complete system catalog definition."""

        for field in fields:
            statement = postgresql_insert(system_catalog_extension_fields_table).values(
                id=field.id,
                system_catalog_key=field.system_catalog_key,
                code=field.code,
                label=field.label,
                value_type=field.value_type.value,
                dictionary_id=field.dictionary_id,
                mapped_attribute_definition_id=field.mapped_attribute_definition_id,
                is_required=field.is_required,
                show_in_overview=field.show_in_overview,
                field_order=field.field_order,
                is_active=field.is_active,
                created_at=field.created_at,
                updated_at=field.updated_at,
            )
            await self._session.execute(
                statement.on_conflict_do_update(
                    index_elements=[
                        system_catalog_extension_fields_table.c.system_catalog_key,
                        system_catalog_extension_fields_table.c.code,
                    ],
                    set_={
                        "label": field.label,
                        "value_type": field.value_type.value,
                        "dictionary_id": field.dictionary_id,
                        "mapped_attribute_definition_id": field.mapped_attribute_definition_id,
                        "is_required": field.is_required,
                        "show_in_overview": field.show_in_overview,
                        "field_order": field.field_order,
                        "is_active": field.is_active,
                        "updated_at": field.updated_at,
                    },
                ),
            )

        await self._session.execute(
            delete(system_catalog_display_modes_table).where(
                system_catalog_display_modes_table.c.system_catalog_key == system_catalog_key,
            ),
        )
        for display_mode in display_modes:
            await self._insert_display_mode(display_mode)

        return await self.get_definition(system_catalog_key)

    async def dictionary_exists(self, dictionary_id: UUID) -> bool:
        """Return whether a dictionary row exists."""

        return bool(
            await self._session.scalar(
                select(exists().where(dictionaries_table.c.id == dictionary_id)),
            ),
        )

    async def active_dictionary_exists(self, dictionary_id: UUID) -> bool:
        """Return whether an active dictionary row exists."""

        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        dictionaries_table.c.id == dictionary_id,
                        dictionaries_table.c.status == "active",
                    ),
                ),
            ),
        )

    async def attribute_definition_exists(self, attribute_definition_id: UUID) -> bool:
        """Return whether an attribute definition row exists."""

        return bool(
            await self._session.scalar(
                select(exists().where(attribute_definitions_table.c.id == attribute_definition_id)),
            ),
        )

    async def active_attribute_definition_exists(self, attribute_definition_id: UUID) -> bool:
        """Return whether an active attribute definition row exists."""

        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        attribute_definitions_table.c.id == attribute_definition_id,
                        attribute_definitions_table.c.status == "active",
                    ),
                ),
            ),
        )

    async def extension_field_has_values(self, extension_field_id: UUID) -> bool:
        """Return whether any document type stores a value for an extension field."""

        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        document_type_extension_values_table.c.extension_field_id
                        == extension_field_id,
                    ),
                ),
            ),
        )

    async def active_document_types_missing_extension_value(
        self,
        extension_field_id: UUID,
    ) -> bool:
        """Return whether an active document type is missing a value for a field."""

        stored_value = exists().where(
            document_type_extension_values_table.c.document_type_id == document_types_table.c.id,
            document_type_extension_values_table.c.extension_field_id == extension_field_id,
        )
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        document_types_table.c.status == DocumentTypeStatus.ACTIVE.value,
                        ~stored_value,
                    ),
                ),
            ),
        )

    async def _insert_display_mode(self, display_mode: SystemCatalogDisplayMode) -> None:
        await self._session.execute(
            postgresql_insert(system_catalog_display_modes_table).values(
                id=display_mode.id,
                system_catalog_key=display_mode.system_catalog_key,
                name=display_mode.name,
                is_default=display_mode.is_default,
                is_active=display_mode.is_active,
                created_at=display_mode.created_at,
                updated_at=display_mode.updated_at,
            ),
        )
        for part in display_mode.parts:
            await self._session.execute(
                postgresql_insert(system_catalog_display_mode_parts_table).values(
                    id=part.id,
                    display_mode_id=part.display_mode_id,
                    part_order=part.part_order,
                    source_type=part.source_type.value,
                    extension_field_id=part.extension_field_id,
                    separator_before=part.separator_before,
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
