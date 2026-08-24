"""Custom dictionary repository implementations."""

from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.dictionaries.ports import (
    DictionaryEntrySearchResult,
    DictionaryRepository,
)
from docmind_api.domain.dictionaries.models import (
    Dictionary,
    DictionaryEntry,
    DictionaryField,
    DictionaryStatus,
)
from docmind_api.infrastructure.persistence.dictionaries.mappers import (
    coerce_uuid,
    dictionary_from_row,
    entry_from_row,
    field_from_row,
)
from docmind_api.infrastructure.persistence.dictionaries.tables import (
    dictionaries_table,
    dictionary_entries_table,
    dictionary_fields_table,
)


class SqlAlchemyDictionaryRepository(DictionaryRepository):
    """PostgreSQL-backed custom dictionary repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_dictionary(self, dictionary: Dictionary) -> bool:
        statement = postgresql_insert(dictionaries_table).values(
            id=dictionary.id,
            external_id=dictionary.external_id,
            name=dictionary.name,
            description=dictionary.description,
            status=dictionary.status.value,
            schema_version=dictionary.schema_version,
            entries_version=dictionary.entries_version,
            created_at=dictionary.created_at,
            updated_at=dictionary.updated_at,
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing().returning(dictionaries_table.c.id),
        )
        return result.scalar_one_or_none() is not None

    async def get_dictionary_by_id(self, dictionary_id: UUID | str) -> Dictionary | None:
        normalized_id = coerce_uuid(dictionary_id)
        if normalized_id is not None:
            statement = select(dictionaries_table).where(dictionaries_table.c.id == normalized_id)
            result = await self._session.execute(statement)
            row = result.mappings().one_or_none()
            if row is not None:
                return dictionary_from_row(row)
            return None

        return await self.get_dictionary_by_external_id(str(dictionary_id))

    async def get_dictionary_by_external_id(self, external_id: str) -> Dictionary | None:
        statement = select(dictionaries_table).where(
            dictionaries_table.c.external_id == external_id,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return dictionary_from_row(row)

    async def list_dictionaries(
        self,
        *,
        status: DictionaryStatus | None = None,
        search: str | None = None,
    ) -> tuple[Dictionary, ...]:
        statement = select(dictionaries_table)
        if status is not None:
            statement = statement.where(dictionaries_table.c.status == status.value)
        if search is not None:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    dictionaries_table.c.name.ilike(pattern),
                    dictionaries_table.c.external_id.ilike(pattern),
                ),
            )
        statement = statement.order_by(
            dictionaries_table.c.name.asc(),
            dictionaries_table.c.external_id.asc(),
        )
        result = await self._session.execute(statement)
        return tuple(dictionary_from_row(row) for row in result.mappings())

    async def update_dictionary_business_fields(self, dictionary: Dictionary) -> bool:
        statement = (
            update(dictionaries_table)
            .where(dictionaries_table.c.id == dictionary.id)
            .values(
                name=dictionary.name,
                description=dictionary.description,
                updated_at=dictionary.updated_at,
            )
            .returning(dictionaries_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def update_dictionary_status(self, dictionary: Dictionary) -> bool:
        statement = (
            update(dictionaries_table)
            .where(dictionaries_table.c.id == dictionary.id)
            .values(status=dictionary.status.value, updated_at=dictionary.updated_at)
            .returning(dictionaries_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def update_dictionary_versions(self, dictionary: Dictionary) -> bool:
        statement = (
            update(dictionaries_table)
            .where(dictionaries_table.c.id == dictionary.id)
            .values(
                schema_version=dictionary.schema_version,
                entries_version=dictionary.entries_version,
                updated_at=dictionary.updated_at,
            )
            .returning(dictionaries_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def delete_dictionary_by_id(self, dictionary_id: UUID | str) -> bool:
        normalized_id = await self._resolve_dictionary_id(dictionary_id)
        if normalized_id is None:
            return False
        await self._session.execute(
            delete(dictionary_fields_table).where(
                dictionary_fields_table.c.dictionary_id == normalized_id,
            ),
        )
        statement = (
            delete(dictionaries_table)
            .where(dictionaries_table.c.id == normalized_id)
            .returning(dictionaries_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def list_fields(
        self,
        dictionary_id: UUID | str,
        *,
        status: DictionaryStatus | None = None,
    ) -> tuple[DictionaryField, ...]:
        normalized_id = await self._resolve_dictionary_id(dictionary_id)
        if normalized_id is None:
            return ()
        statement = select(dictionary_fields_table).where(
            dictionary_fields_table.c.dictionary_id == normalized_id,
        )
        if status is not None:
            statement = statement.where(dictionary_fields_table.c.status == status.value)
        statement = statement.order_by(
            dictionary_fields_table.c.sort_order.asc(),
            dictionary_fields_table.c.label.asc(),
            dictionary_fields_table.c.external_id.asc(),
        )
        result = await self._session.execute(statement)
        return tuple(field_from_row(row) for row in result.mappings())

    async def replace_fields(
        self,
        dictionary_id: UUID | str,
        fields: tuple[DictionaryField, ...],
    ) -> None:
        normalized_id = await self._resolve_dictionary_id(dictionary_id)
        if normalized_id is None:
            return
        field_external_ids = tuple(field.external_id for field in fields)
        delete_statement = delete(dictionary_fields_table).where(
            dictionary_fields_table.c.dictionary_id == normalized_id,
        )
        if field_external_ids:
            delete_statement = delete_statement.where(
                dictionary_fields_table.c.external_id.not_in(field_external_ids),
            )
        await self._session.execute(delete_statement)
        for field in fields:
            statement = postgresql_insert(dictionary_fields_table).values(
                id=field.id,
                dictionary_id=normalized_id,
                external_id=field.external_id,
                label=field.label,
                data_type=field.data_type.value,
                required=field.required,
                constraints=field.constraints.as_json(),
                normalization=dict(field.normalization),
                format=dict(field.format),
                is_unique=field.is_unique,
                sort_order=field.sort_order,
                status=field.status.value,
                created_at=field.created_at,
                updated_at=field.updated_at,
            )
            await self._session.execute(
                statement.on_conflict_do_update(
                    index_elements=[
                        dictionary_fields_table.c.dictionary_id,
                        dictionary_fields_table.c.external_id,
                    ],
                    set_={
                        "label": field.label,
                        "data_type": field.data_type.value,
                        "required": field.required,
                        "constraints": field.constraints.as_json(),
                        "normalization": dict(field.normalization),
                        "format": dict(field.format),
                        "is_unique": field.is_unique,
                        "sort_order": field.sort_order,
                        "status": field.status.value,
                        "updated_at": field.updated_at,
                    },
                ),
            )

    async def add_entry(self, entry: DictionaryEntry) -> bool:
        statement = postgresql_insert(dictionary_entries_table).values(
            id=entry.id,
            dictionary_id=entry.dictionary_id,
            external_id=entry.external_id,
            label=entry.label,
            values=dict(entry.values),
            status=entry.status.value,
            sort_order=entry.sort_order,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing().returning(dictionary_entries_table.c.id),
        )
        return result.scalar_one_or_none() is not None

    async def get_entry_by_id(
        self,
        dictionary_id: UUID | str,
        entry_id: UUID | str,
    ) -> DictionaryEntry | None:
        normalized_dictionary_id = await self._resolve_dictionary_id(dictionary_id)
        normalized_entry_id = coerce_uuid(entry_id)
        if normalized_dictionary_id is None or normalized_entry_id is None:
            return None
        statement = select(dictionary_entries_table).where(
            dictionary_entries_table.c.dictionary_id == normalized_dictionary_id,
            dictionary_entries_table.c.id == normalized_entry_id,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return entry_from_row(row)

    async def get_entry_by_external_id(
        self,
        dictionary_id: UUID | str,
        external_id: str,
    ) -> DictionaryEntry | None:
        normalized_dictionary_id = await self._resolve_dictionary_id(dictionary_id)
        if normalized_dictionary_id is None:
            return None
        statement = select(dictionary_entries_table).where(
            dictionary_entries_table.c.dictionary_id == normalized_dictionary_id,
            dictionary_entries_table.c.external_id == external_id,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return entry_from_row(row)

    async def search_entries(
        self,
        dictionary_id: UUID | str,
        *,
        status: DictionaryStatus | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DictionaryEntrySearchResult:
        normalized_dictionary_id = await self._resolve_dictionary_id(dictionary_id)
        if normalized_dictionary_id is None:
            return DictionaryEntrySearchResult(entries=(), total_count=0)
        statement = select(dictionary_entries_table).where(
            dictionary_entries_table.c.dictionary_id == normalized_dictionary_id,
        )
        count_statement = select(func.count(dictionary_entries_table.c.id)).where(
            dictionary_entries_table.c.dictionary_id == normalized_dictionary_id,
        )
        if status is not None:
            statement = statement.where(dictionary_entries_table.c.status == status.value)
            count_statement = count_statement.where(
                dictionary_entries_table.c.status == status.value,
            )
        if search is not None:
            pattern = f"%{search}%"
            search_filter = or_(
                dictionary_entries_table.c.label.ilike(pattern),
                dictionary_entries_table.c.external_id.ilike(pattern),
            )
            statement = statement.where(search_filter)
            count_statement = count_statement.where(search_filter)
        statement = statement.order_by(
            dictionary_entries_table.c.sort_order.asc().nullslast(),
            dictionary_entries_table.c.label.asc(),
            dictionary_entries_table.c.external_id.asc(),
        )
        if limit > 0:
            statement = statement.limit(limit).offset(offset)
        result = await self._session.execute(statement)
        total_count = await self._session.scalar(count_statement)
        return DictionaryEntrySearchResult(
            entries=tuple(entry_from_row(row) for row in result.mappings()),
            total_count=total_count or 0,
        )

    async def update_entry_business_fields(self, entry: DictionaryEntry) -> bool:
        statement = (
            update(dictionary_entries_table)
            .where(dictionary_entries_table.c.id == entry.id)
            .values(
                external_id=entry.external_id,
                label=entry.label,
                values=dict(entry.values),
                sort_order=entry.sort_order,
                updated_at=entry.updated_at,
            )
            .returning(dictionary_entries_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def update_entry_status(self, entry: DictionaryEntry) -> bool:
        statement = (
            update(dictionary_entries_table)
            .where(dictionary_entries_table.c.id == entry.id)
            .values(status=entry.status.value, updated_at=entry.updated_at)
            .returning(dictionary_entries_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def delete_entry_by_id(
        self,
        dictionary_id: UUID | str,
        entry_id: UUID | str,
    ) -> bool:
        normalized_dictionary_id = await self._resolve_dictionary_id(dictionary_id)
        normalized_entry_id = coerce_uuid(entry_id)
        if normalized_dictionary_id is None or normalized_entry_id is None:
            return False
        statement = (
            delete(dictionary_entries_table)
            .where(
                dictionary_entries_table.c.dictionary_id == normalized_dictionary_id,
                dictionary_entries_table.c.id == normalized_entry_id,
            )
            .returning(dictionary_entries_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def _resolve_dictionary_id(self, dictionary_id: UUID | str) -> UUID | None:
        normalized_id = coerce_uuid(dictionary_id)
        if normalized_id is not None:
            existing_id = await self._session.scalar(
                select(dictionaries_table.c.id).where(dictionaries_table.c.id == normalized_id),
            )
            if existing_id is not None:
                return existing_id
            return None
        dictionary = await self.get_dictionary_by_external_id(str(dictionary_id))
        if dictionary is None:
            return None
        return UUID(str(dictionary.id))
