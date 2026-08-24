"""System attribute category repository implementations."""

from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.attributes.ports import (
    AttributeCategoryRepository,
    AttributeCategoryUsageRepository,
)
from docmind_api.domain.attributes.models import (
    AttributeCategory,
    AttributeCategoryUsage,
    AttributeStatus,
)
from docmind_api.infrastructure.persistence.attributes.tables import (
    attribute_categories_table,
    attribute_definitions_table,
)


class SqlAlchemyAttributeCategoryRepository(AttributeCategoryRepository):
    """PostgreSQL-backed system attribute category repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, category: AttributeCategory) -> bool:
        statement = postgresql_insert(attribute_categories_table).values(
            id=category.id,
            external_id=category.external_id,
            label=category.label,
            flags=dict(category.flags),
            status=category.status.value,
            created_at=category.created_at,
            updated_at=category.updated_at,
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing().returning(attribute_categories_table.c.id),
        )
        return result.scalar_one_or_none() is not None

    async def get_by_id(self, category_id: UUID | str) -> AttributeCategory | None:
        normalized_id = _coerce_uuid(category_id)
        if normalized_id is None:
            return await self.get_by_external_id(str(category_id))

        statement = select(attribute_categories_table).where(
            attribute_categories_table.c.id == normalized_id,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _attribute_category_from_row(row)

    async def get_by_external_id(self, external_id: str) -> AttributeCategory | None:
        statement = select(attribute_categories_table).where(
            attribute_categories_table.c.external_id == external_id,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _attribute_category_from_row(row)

    async def list(self, *, active_only: bool = True) -> tuple[AttributeCategory, ...]:
        statement = select(attribute_categories_table)
        if active_only:
            statement = statement.where(
                attribute_categories_table.c.status == AttributeStatus.ACTIVE.value,
            )
        statement = statement.order_by(
            attribute_categories_table.c.label.asc(),
            attribute_categories_table.c.external_id.asc(),
        )
        result = await self._session.execute(statement)
        return tuple(_attribute_category_from_row(row) for row in result.mappings())

    async def update_business_fields(self, category: AttributeCategory) -> bool:
        statement = (
            update(attribute_categories_table)
            .where(attribute_categories_table.c.id == category.id)
            .values(
                label=category.label,
                flags=dict(category.flags),
                updated_at=category.updated_at,
            )
            .returning(attribute_categories_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def update_status(self, category: AttributeCategory) -> bool:
        statement = (
            update(attribute_categories_table)
            .where(attribute_categories_table.c.id == category.id)
            .values(status=category.status.value, updated_at=category.updated_at)
            .returning(attribute_categories_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def delete_by_id(self, category_id: UUID | str) -> bool:
        normalized_id = await self._resolve_category_id(category_id)
        if normalized_id is None:
            return False

        statement = (
            delete(attribute_categories_table)
            .where(attribute_categories_table.c.id == normalized_id)
            .returning(attribute_categories_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def _resolve_category_id(self, category_id: UUID | str) -> UUID | None:
        normalized_id = _coerce_uuid(category_id)
        if normalized_id is not None:
            existing_id = await self._session.scalar(
                select(attribute_categories_table.c.id).where(
                    attribute_categories_table.c.id == normalized_id,
                ),
            )
            if existing_id is not None:
                return existing_id

        category = await self.get_by_external_id(str(category_id))
        if category is None:
            return None
        return UUID(str(category.id))


class SqlAlchemyAttributeCategoryUsageRepository(AttributeCategoryUsageRepository):
    """Attribute category dependency reader used by lifecycle guards."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_usage(self, category_id: UUID | str) -> AttributeCategoryUsage:
        normalized_id = await _resolve_category_id(self._session, category_id)
        if normalized_id is None:
            return AttributeCategoryUsage()

        attributes_statement = select(func.count(attribute_definitions_table.c.id)).where(
            attribute_definitions_table.c.category_id == normalized_id,
        )
        active_attributes_statement = select(
            func.count(attribute_definitions_table.c.id),
        ).where(
            attribute_definitions_table.c.category_id == normalized_id,
            attribute_definitions_table.c.status == AttributeStatus.ACTIVE.value,
        )
        attribute_count = await self._session.scalar(attributes_statement)
        active_attribute_count = await self._session.scalar(active_attributes_statement)
        return AttributeCategoryUsage(
            attribute_definitions=attribute_count or 0,
            active_attribute_definitions=active_attribute_count or 0,
        )


def _attribute_category_from_row(row: Mapping[Any, Any]) -> AttributeCategory:
    flags = cast(dict[str, bool], row["flags"])
    return AttributeCategory(
        id=row["id"],
        external_id=row["external_id"],
        label=row["label"],
        flags=flags,
        status=AttributeStatus(row["status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _coerce_uuid(value: UUID | str) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


async def _resolve_category_id(
    session: AsyncSession,
    category_id: UUID | str,
) -> UUID | None:
    normalized_id = _coerce_uuid(category_id)
    if normalized_id is not None:
        existing_id = await session.scalar(
            select(attribute_categories_table.c.id).where(
                attribute_categories_table.c.id == normalized_id,
            ),
        )
        if existing_id is not None:
            return existing_id

    statement = select(attribute_categories_table.c.id).where(
        attribute_categories_table.c.external_id == str(category_id),
    )
    return await session.scalar(statement)
