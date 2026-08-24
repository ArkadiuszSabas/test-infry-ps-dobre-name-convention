"""Document type catalog repository implementations."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.document_types.ports import (
    DocumentTypeCatalogRepository,
    DocumentTypeUsageRepository,
)
from docmind_api.domain.document_types.models import (
    DocumentType,
    DocumentTypeStatus,
    DocumentTypeUsage,
)
from docmind_api.infrastructure.persistence.attribute_requirements.tables import (
    attribute_requirements_table,
)
from docmind_api.infrastructure.persistence.dictionaries.tables import dictionary_entries_table
from docmind_api.infrastructure.persistence.document_types.tables import document_types_table
from docmind_api.infrastructure.persistence.documents.tables import documents_table
from docmind_api.infrastructure.persistence.system_catalogs.tables import (
    document_type_extension_values_table,
    system_catalog_extension_fields_table,
)


class SqlAlchemyDocumentTypeCatalogRepository(DocumentTypeCatalogRepository):
    """PostgreSQL-backed document type catalog repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document_type: DocumentType) -> bool:
        """Store a document type if its technical id is still available."""

        statement = postgresql_insert(document_types_table).values(
            id=document_type.id,
            external_id=document_type.external_id,
            name=document_type.name,
            description=document_type.description,
            status=document_type.status.value,
            created_at=document_type.created_at,
            updated_at=document_type.updated_at,
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing().returning(document_types_table.c.id),
        )
        return result.scalar_one_or_none() is not None

    async def get_by_id(self, document_type_id: UUID | str) -> DocumentType | None:
        """Return a document type by technical id or external business id."""

        normalized_id = _coerce_uuid(document_type_id)
        if normalized_id is not None:
            statement = select(document_types_table).where(
                document_types_table.c.id == normalized_id,
            )
            result = await self._session.execute(statement)
            row = result.mappings().one_or_none()
            if row is not None:
                return _document_type_from_row(row)

        return await self.get_by_external_id(str(document_type_id))

    async def get_by_external_id(self, external_id: str) -> DocumentType | None:
        """Return a document type by stable business id."""

        statement = select(document_types_table).where(
            document_types_table.c.external_id == external_id,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _document_type_from_row(row)

    async def find_active_by_name_and_parameters(
        self,
        *,
        name: str,
        parameters: Mapping[str, str],
    ) -> tuple[DocumentType, ...]:
        """Find active types by exact base name and catalog parameter values."""

        value_source = document_type_extension_values_table.join(
            system_catalog_extension_fields_table,
            document_type_extension_values_table.c.extension_field_id
            == system_catalog_extension_fields_table.c.id,
        ).outerjoin(
            dictionary_entries_table,
            document_type_extension_values_table.c.dictionary_entry_id
            == dictionary_entries_table.c.id,
        )
        statement = select(document_types_table).where(
            document_types_table.c.name == name,
            document_types_table.c.status == DocumentTypeStatus.ACTIVE.value,
        )
        for code, value in parameters.items():
            statement = statement.where(
                exists(
                    select(1)
                    .select_from(value_source)
                    .where(
                        document_type_extension_values_table.c.document_type_id
                        == document_types_table.c.id,
                        system_catalog_extension_fields_table.c.system_catalog_key
                        == "document_type",
                        system_catalog_extension_fields_table.c.code == code,
                        system_catalog_extension_fields_table.c.is_active.is_(True),
                        or_(
                            dictionary_entries_table.c.label == value,
                            dictionary_entries_table.c.external_id == value,
                            document_type_extension_values_table.c.text_value == value,
                        ),
                        or_(
                            dictionary_entries_table.c.id.is_(None),
                            dictionary_entries_table.c.status == "active",
                        ),
                    )
                )
            )
        result = await self._session.execute(statement)
        return tuple(_document_type_from_row(row) for row in result.mappings())

    async def list_active(self) -> tuple[DocumentType, ...]:
        """Return active document types ordered for catalog display and classification."""

        statement = (
            select(document_types_table)
            .where(document_types_table.c.status == DocumentTypeStatus.ACTIVE.value)
            .order_by(
                document_types_table.c.name.asc(),
                document_types_table.c.external_id.asc(),
            )
        )
        result = await self._session.execute(statement)
        return tuple(_document_type_from_row(row) for row in result.mappings())

    async def list_all(self) -> tuple[DocumentType, ...]:
        """Return all document types ordered for administration."""

        statement = select(document_types_table).order_by(
            document_types_table.c.name.asc(),
            document_types_table.c.external_id.asc(),
        )
        result = await self._session.execute(statement)
        return tuple(_document_type_from_row(row) for row in result.mappings())

    async def update_business_fields(self, document_type: DocumentType) -> bool:
        """Update editable business fields while preserving stable technical fields."""

        statement = (
            update(document_types_table)
            .where(document_types_table.c.id == document_type.id)
            .values(
                external_id=document_type.external_id,
                name=document_type.name,
                description=document_type.description,
                updated_at=document_type.updated_at,
            )
            .returning(document_types_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def update_status(self, document_type: DocumentType) -> bool:
        """Persist a status transition for a document type."""

        statement = (
            update(document_types_table)
            .where(document_types_table.c.id == document_type.id)
            .values(
                status=document_type.status.value,
                updated_at=document_type.updated_at,
            )
            .returning(document_types_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def delete_by_id(self, document_type_id: UUID | str) -> bool:
        """Permanently remove a document type by technical id or external business id."""

        normalized_id = await self._resolve_document_type_id(document_type_id)
        if normalized_id is None:
            return False

        statement = (
            delete(document_types_table)
            .where(document_types_table.c.id == normalized_id)
            .returning(document_types_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def _resolve_document_type_id(self, document_type_id: UUID | str) -> UUID | None:
        normalized_id = _coerce_uuid(document_type_id)
        if normalized_id is not None:
            existing_id = await self._session.scalar(
                select(document_types_table.c.id).where(
                    document_types_table.c.id == normalized_id,
                ),
            )
            if existing_id is not None:
                return existing_id

        document_type = await self.get_by_external_id(str(document_type_id))
        if document_type is None:
            return None
        return UUID(str(document_type.id))


class SqlAlchemyDocumentTypeUsageRepository(DocumentTypeUsageRepository):
    """Document type dependency reader used by deletion guards."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_usage(self, document_type_id: UUID | str) -> DocumentTypeUsage:
        """Return blocking usage counts for a document type."""

        normalized_id = await _resolve_document_type_id(
            self._session,
            document_type_id,
        )
        if normalized_id is None:
            return DocumentTypeUsage()

        attribute_mapping_statement = select(
            func.count(attribute_requirements_table.c.attribute_definition_id),
        ).where(
            attribute_requirements_table.c.document_type_id == normalized_id,
        )
        attribute_mapping_count = await self._session.scalar(attribute_mapping_statement)
        historical_documents_statement = select(func.count(documents_table.c.id)).where(
            documents_table.c.document_type_id == normalized_id,
        )
        historical_document_count = await self._session.scalar(historical_documents_statement)
        return DocumentTypeUsage(
            attribute_mappings=attribute_mapping_count or 0,
            historical_documents=historical_document_count or 0,
        )


def _document_type_from_row(row: Mapping[Any, Any]) -> DocumentType:
    return DocumentType(
        id=row["id"],
        external_id=row["external_id"],
        name=row["name"],
        description=row["description"],
        status=DocumentTypeStatus(row["status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _coerce_uuid(value: UUID | str) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


async def _resolve_document_type_id(
    session: AsyncSession,
    document_type_id: UUID | str,
) -> UUID | None:
    normalized_id = _coerce_uuid(document_type_id)
    if normalized_id is not None:
        existing_id = await session.scalar(
            select(document_types_table.c.id).where(
                document_types_table.c.id == normalized_id,
            ),
        )
        if existing_id is not None:
            return existing_id

    statement = select(document_types_table.c.id).where(
        document_types_table.c.external_id == str(document_type_id),
    )
    return await session.scalar(statement)
