"""Document registry repository implementations."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.documents.ports import DocumentRegistryRepository
from docmind_api.domain.documents.metadata import JsonScalar
from docmind_api.domain.documents.models import (
    DocumentRecord,
    DocumentSource,
    DocumentStatus,
    DocumentUploadActor,
    StorageLocator,
)
from docmind_api.infrastructure.persistence.documents.deletion_tables import (
    document_is_not_deleting,
)
from docmind_api.infrastructure.persistence.documents.tables import (
    document_type_change_audit_events_table,
    documents_table,
)


class SqlAlchemyDocumentRegistryRepository(DocumentRegistryRepository):
    """PostgreSQL-backed document registry repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, document: DocumentRecord) -> bool:
        """Store a document if its id is still available."""

        statement = postgresql_insert(documents_table).values(
            id=document.id,
            external_id=document.external_id,
            name=document.name,
            original_filename=document.original_filename,
            document_type_id=document.document_type_id,
            status=document.status.value,
            source=document.source.source,
            connector=document.source.connector,
            connector_instance_id=document.source.connector_instance_id,
            connector_correlation_id=document.source.correlation_id,
            storage_locator=document.storage_locator.value,
            content_size_bytes=document.content_size_bytes,
            metadata_values=dict(document.metadata_values),
            uploaded_by_user_id=(
                document.uploaded_by.user_id if document.uploaded_by is not None else None
            ),
            uploaded_by_display_name=(
                document.uploaded_by.display_name if document.uploaded_by is not None else None
            ),
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing(
                index_elements=[documents_table.c.id],
            ).returning(documents_table.c.id),
        )
        return result.scalar_one_or_none() is not None

    async def get_by_id(self, document_id: UUID) -> DocumentRecord | None:
        """Return a document registry entry by id."""

        statement = select(documents_table).where(
            documents_table.c.id == document_id,
            document_is_not_deleting(document_id),
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return document_from_row(row)

    async def get_by_id_for_update(self, document_id: UUID) -> DocumentRecord | None:
        """Lock one document while a reviewer evaluates and changes its type."""

        result = await self._session.execute(
            select(documents_table)
            .where(
                documents_table.c.id == document_id,
                document_is_not_deleting(document_id),
            )
            .with_for_update()
        )
        row = result.mappings().one_or_none()
        return document_from_row(row) if row is not None else None

    async def change_document_type(
        self,
        *,
        document_id: UUID,
        document_type_id: UUID,
        actor_id: str,
        reason: str | None,
        changed_at: datetime,
    ) -> DocumentRecord | None:
        existing = await self.get_by_id_for_update(document_id)
        if existing is None:
            return None
        if existing.document_type_id == document_type_id:
            return existing
        await self._session.execute(
            update(documents_table)
            .where(documents_table.c.id == document_id)
            .values(document_type_id=document_type_id, updated_at=changed_at)
        )
        await self._session.execute(
            postgresql_insert(document_type_change_audit_events_table).values(
                id=uuid4(),
                document_id=document_id,
                old_document_type_id=existing.document_type_id,
                new_document_type_id=document_type_id,
                actor_id=actor_id,
                reason=reason.strip() if reason else None,
                changed_at=changed_at,
            )
        )
        return DocumentRecord(
            id=existing.id,
            external_id=existing.external_id,
            name=existing.name,
            original_filename=existing.original_filename,
            document_type_id=document_type_id,
            status=existing.status,
            source=existing.source,
            storage_locator=existing.storage_locator,
            content_size_bytes=existing.content_size_bytes,
            metadata_values=existing.metadata_values,
            uploaded_by=existing.uploaded_by,
            created_at=existing.created_at,
            updated_at=changed_at,
        )

    async def list(
        self,
        *,
        source: str | None = None,
        connector: str | None = None,
        archived: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[DocumentRecord, ...]:
        """Return document registry entries, newest first."""

        statement = select(documents_table).order_by(
            documents_table.c.created_at.desc(),
            documents_table.c.id.desc(),
        )
        statement = statement.where(document_is_not_deleting(documents_table.c.id))
        if source is not None:
            statement = statement.where(documents_table.c.source == source)
        if connector is not None:
            statement = statement.where(documents_table.c.connector == connector)
        if archived is True:
            statement = statement.where(documents_table.c.status == DocumentStatus.APPROVED.value)
        elif archived is False:
            statement = statement.where(documents_table.c.status != DocumentStatus.APPROVED.value)

        statement = statement.limit(limit).offset(offset)
        result = await self._session.execute(statement)
        return tuple(document_from_row(row) for row in result.mappings())


def document_from_row(row: Mapping[Any, Any]) -> DocumentRecord:
    metadata_values = cast(dict[str, JsonScalar], row["metadata_values"])
    return DocumentRecord(
        id=cast(UUID, row["id"]),
        external_id=row["external_id"],
        name=row["name"],
        original_filename=row["original_filename"],
        document_type_id=row["document_type_id"],
        status=DocumentStatus(row["status"]),
        source=DocumentSource(
            source=row["source"],
            connector=row["connector"],
            connector_instance_id=row["connector_instance_id"],
            correlation_id=row["connector_correlation_id"],
        ),
        storage_locator=StorageLocator(row["storage_locator"]),
        content_size_bytes=row["content_size_bytes"],
        metadata_values=metadata_values,
        uploaded_by=_uploaded_by_from_row(row),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _uploaded_by_from_row(row: Mapping[Any, Any]) -> DocumentUploadActor | None:
    user_id = row["uploaded_by_user_id"]
    display_name = row["uploaded_by_display_name"]
    if user_id is None or display_name is None:
        return None

    return DocumentUploadActor(
        user_id=user_id,
        display_name=display_name,
    )
