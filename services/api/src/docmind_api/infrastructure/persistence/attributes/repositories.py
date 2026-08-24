"""Attribute definition catalog repository implementations."""

from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from sqlalchemy import String, delete, func, select, update
from sqlalchemy import cast as sql_cast
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.attributes.ports import (
    AttributeCategoryCount,
    AttributeDefinitionRepository,
    AttributeDefinitionUsageRepository,
)
from docmind_api.domain.attributes.models import (
    AttributeConstraints,
    AttributeDataType,
    AttributeDefinition,
    AttributeDefinitionUsage,
    AttributeSource,
    AttributeStatus,
    AttributeValueSource,
)
from docmind_api.domain.document_types.models import DocumentTypeStatus
from docmind_api.infrastructure.persistence.attribute_requirements.tables import (
    attribute_requirements_table,
)
from docmind_api.infrastructure.persistence.attributes.tables import (
    attribute_categories_table,
    attribute_definitions_table,
)
from docmind_api.infrastructure.persistence.document_types.tables import document_types_table
from docmind_api.infrastructure.persistence.documents.tables import documents_table
from docmind_api.infrastructure.persistence.system_catalogs.tables import (
    system_catalog_extension_fields_table,
)


class SqlAlchemyAttributeDefinitionRepository(AttributeDefinitionRepository):
    """PostgreSQL-backed attribute definition catalog repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, attribute: AttributeDefinition) -> bool:
        """Store an attribute definition if its technical id is still available."""

        statement = postgresql_insert(attribute_definitions_table).values(
            id=attribute.id,
            external_id=attribute.external_id,
            name=attribute.name,
            category_id=attribute.category_id,
            data_type=attribute.data_type.value,
            constraints=attribute.constraints.as_json(),
            allowed_values=list(attribute.allowed_values),
            value_source=attribute.value_source.value,
            dictionary_id=attribute.dictionary_id,
            source=attribute.source.value,
            comment=attribute.comment,
            llm_context=attribute.llm_context,
            status=attribute.status.value,
            schema_version=attribute.schema_version,
            created_at=attribute.created_at,
            updated_at=attribute.updated_at,
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing().returning(attribute_definitions_table.c.id),
        )
        return result.scalar_one_or_none() is not None

    async def get_by_id(self, attribute_id: UUID | str) -> AttributeDefinition | None:
        """Return an attribute definition by stable technical id."""

        normalized_id = _coerce_uuid(attribute_id)
        if normalized_id is None:
            return await self.get_by_external_id(str(attribute_id))

        statement = _attribute_definition_select().where(
            attribute_definitions_table.c.id == normalized_id,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _attribute_definition_from_row(row)

    async def get_by_external_id(self, external_id: str) -> AttributeDefinition | None:
        """Return an attribute definition by stable business id."""

        statement = _attribute_definition_select().where(
            attribute_definitions_table.c.external_id == external_id,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _attribute_definition_from_row(row)

    async def list(
        self,
        *,
        category: str | None = None,
    ) -> tuple[AttributeDefinition, ...]:
        """Return attribute definitions ordered for catalog display."""

        statement = _attribute_definition_select()
        if category is not None:
            statement = statement.where(attribute_categories_table.c.label == category)

        statement = statement.order_by(
            attribute_categories_table.c.label.asc(),
            attribute_definitions_table.c.name.asc(),
            attribute_definitions_table.c.external_id.asc(),
        )
        result = await self._session.execute(statement)
        return tuple(_attribute_definition_from_row(row) for row in result.mappings())

    async def count_by_category(self) -> tuple[AttributeCategoryCount, ...]:
        """Return attribute definition counts grouped by display category."""

        statement = (
            select(
                attribute_categories_table.c.label.label("category"),
                func.count(attribute_definitions_table.c.id).label("count"),
            )
            .join(
                attribute_categories_table,
                attribute_definitions_table.c.category_id == attribute_categories_table.c.id,
            )
            .group_by(attribute_categories_table.c.label)
            .order_by(attribute_categories_table.c.label.asc())
        )
        result = await self._session.execute(statement)
        return tuple(
            AttributeCategoryCount(category=row["category"], count=row["count"])
            for row in result.mappings()
        )

    async def update_business_fields(self, attribute: AttributeDefinition) -> bool:
        """Update editable business fields while preserving stable technical fields."""

        statement = (
            update(attribute_definitions_table)
            .where(attribute_definitions_table.c.id == attribute.id)
            .values(
                external_id=attribute.external_id,
                name=attribute.name,
                category_id=attribute.category_id,
                data_type=attribute.data_type.value,
                constraints=attribute.constraints.as_json(),
                allowed_values=list(attribute.allowed_values),
                value_source=attribute.value_source.value,
                dictionary_id=attribute.dictionary_id,
                source=attribute.source.value,
                comment=attribute.comment,
                llm_context=attribute.llm_context,
                schema_version=attribute.schema_version,
                updated_at=attribute.updated_at,
            )
            .returning(attribute_definitions_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def update_status(self, attribute: AttributeDefinition) -> bool:
        """Persist a status transition for an attribute definition."""

        statement = (
            update(attribute_definitions_table)
            .where(attribute_definitions_table.c.id == attribute.id)
            .values(
                status=attribute.status.value,
                schema_version=attribute.schema_version,
                updated_at=attribute.updated_at,
            )
            .returning(attribute_definitions_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def delete_by_id(self, attribute_id: UUID | str) -> bool:
        """Permanently remove an attribute definition by stable technical id."""

        normalized_id = await self._resolve_attribute_id(attribute_id)
        if normalized_id is None:
            return False

        statement = (
            delete(attribute_definitions_table)
            .where(attribute_definitions_table.c.id == normalized_id)
            .returning(attribute_definitions_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def _resolve_attribute_id(self, attribute_id: UUID | str) -> UUID | None:
        normalized_id = _coerce_uuid(attribute_id)
        if normalized_id is not None:
            return normalized_id

        attribute = await self.get_by_external_id(str(attribute_id))
        if attribute is None:
            return None
        return UUID(str(attribute.id))


class SqlAlchemyAttributeDefinitionUsageRepository(AttributeDefinitionUsageRepository):
    """Attribute definition dependency reader used by deletion guards."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_usage(self, attribute_id: UUID | str) -> AttributeDefinitionUsage:
        """Return blocking usage counts for an attribute definition."""

        normalized_id = await _resolve_attribute_id(self._session, attribute_id)
        if normalized_id is None:
            return AttributeDefinitionUsage()

        mappings_statement = select(
            func.count(
                attribute_requirements_table.c.document_type_id,
            ),
        ).where(attribute_requirements_table.c.attribute_definition_id == normalized_id)
        active_mappings_statement = (
            select(
                func.count(
                    attribute_requirements_table.c.document_type_id,
                ),
            )
            .join(
                document_types_table,
                document_types_table.c.id == attribute_requirements_table.c.document_type_id,
            )
            .where(
                attribute_requirements_table.c.attribute_definition_id == normalized_id,
                document_types_table.c.status == DocumentTypeStatus.ACTIVE.value,
            )
        )
        mapping_count = await self._session.scalar(mappings_statement)
        active_mapping_count = await self._session.scalar(active_mappings_statement)
        system_catalog_field_count = await self._session.scalar(
            select(func.count(system_catalog_extension_fields_table.c.id)).where(
                system_catalog_extension_fields_table.c.mapped_attribute_definition_id
                == normalized_id,
            ),
        )
        active_configuration_count = await self._session.scalar(
            select(func.count(system_catalog_extension_fields_table.c.id)).where(
                system_catalog_extension_fields_table.c.mapped_attribute_definition_id
                == normalized_id,
                system_catalog_extension_fields_table.c.is_active.is_(True),
            ),
        )
        attribute_key = func.coalesce(
            attribute_definitions_table.c.external_id,
            sql_cast(attribute_definitions_table.c.id, String),
        )
        historical_value_count = await self._session.scalar(
            select(func.count(func.distinct(documents_table.c.id)))
            .select_from(documents_table)
            .where(
                select(attribute_definitions_table.c.id)
                .where(
                    attribute_definitions_table.c.id == normalized_id,
                    func.jsonb_exists(documents_table.c.metadata_values, attribute_key),
                )
                .exists(),
            ),
        )
        return AttributeDefinitionUsage(
            document_type_mappings=mapping_count or 0,
            active_document_type_mappings=active_mapping_count or 0,
            system_catalog_fields=system_catalog_field_count or 0,
            active_configurations=active_configuration_count or 0,
            historical_values=historical_value_count or 0,
        )


def _attribute_definition_from_row(row: Mapping[Any, Any]) -> AttributeDefinition:
    allowed_values = cast(list[str], row["allowed_values"])
    constraints = cast(dict[str, object], row["constraints"])
    return AttributeDefinition(
        id=row["id"],
        external_id=row["external_id"],
        name=row["name"],
        category=row["category"],
        category_id=row["category_id"],
        data_type=AttributeDataType(row["data_type"]),
        constraints=AttributeConstraints.from_mapping(constraints),
        allowed_values=tuple(allowed_values),
        value_source=AttributeValueSource(row["value_source"]),
        dictionary_id=row["dictionary_id"],
        source=AttributeSource(row["source"]),
        comment=row["comment"],
        llm_context=row["llm_context"],
        _allow_legacy_llm_context=True,
        status=AttributeStatus(row["status"]),
        schema_version=row["schema_version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _attribute_definition_select():
    return select(
        attribute_definitions_table,
        attribute_categories_table.c.label.label("category"),
    ).join(
        attribute_categories_table,
        attribute_definitions_table.c.category_id == attribute_categories_table.c.id,
    )


def _coerce_uuid(value: UUID | str) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


async def _resolve_attribute_id(
    session: AsyncSession,
    attribute_id: UUID | str,
) -> UUID | None:
    normalized_id = _coerce_uuid(attribute_id)
    if normalized_id is not None:
        return normalized_id

    statement = select(attribute_definitions_table.c.id).where(
        attribute_definitions_table.c.external_id == str(attribute_id),
    )
    return await session.scalar(statement)
