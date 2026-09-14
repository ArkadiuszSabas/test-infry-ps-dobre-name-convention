"""Document registry repository implementations."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import String, case, func, or_, select, update
from sqlalchemy import cast as sql_cast
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.documents.ports import DocumentRegistryRepository
from docmind_api.application.documents.read_models import (
    DocumentListEntry,
    DocumentListQuery,
    DocumentListSortField,
    DocumentListStatus,
)
from docmind_api.application.listing import ListSortDirection
from docmind_api.domain.documents.metadata import JsonScalar
from docmind_api.domain.documents.models import (
    DocumentRecord,
    DocumentSource,
    DocumentStatus,
    DocumentUploadActor,
    StorageLocator,
)
from docmind_api.infrastructure.persistence.document_types.tables import document_types_table
from docmind_api.infrastructure.persistence.documents.deletion_tables import (
    document_is_not_deleting,
)
from docmind_api.infrastructure.persistence.documents.tables import (
    document_type_change_audit_events_table,
    documents_table,
)
from docmind_api.infrastructure.persistence.list_sorting import stable_order_by
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.tables import (
    ocr_pipeline_runs_table,
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

    async def list(self, query: DocumentListQuery) -> tuple[DocumentListEntry, ...]:
        """Return one filtered, deterministically sorted document page."""

        visible_status = _visible_status_expression()
        statement = self._filtered_statement(
            query,
            columns=(documents_table, visible_status),
            visible_status=visible_status,
        ).order_by(*_document_ordering(query, visible_status))
        statement = statement.limit(query.limit).offset(query.offset)
        result = await self._session.execute(statement)
        return tuple(
            DocumentListEntry(
                document=document_from_row(row),
                status=DocumentListStatus(row["visible_status"]),
            )
            for row in result.mappings()
        )

    async def count(self, query: DocumentListQuery) -> int:
        result = await self._session.execute(
            self._filtered_statement(query, columns=(func.count(documents_table.c.id),))
        )
        return int(result.scalar_one())

    async def count_statuses(self, query: DocumentListQuery) -> tuple[tuple[str, int], ...]:
        visible_status = _visible_status_expression()
        result = await self._session.execute(
            self._filtered_statement(
                query,
                columns=(visible_status, func.count(documents_table.c.id).label("count")),
                include_status=False,
                visible_status=visible_status,
            )
            .group_by(visible_status)
            .order_by(visible_status)
        )
        return tuple((str(status), int(count)) for status, count in result.tuples())

    async def count_document_types(self, query: DocumentListQuery) -> tuple[tuple[UUID, int], ...]:
        result = await self._session.execute(
            self._filtered_statement(
                query,
                columns=(
                    documents_table.c.document_type_id,
                    func.count(documents_table.c.id).label("count"),
                ),
                include_document_type=False,
            )
            .group_by(documents_table.c.document_type_id)
            .order_by(documents_table.c.document_type_id)
        )
        return tuple((document_type_id, int(count)) for document_type_id, count in result.tuples())

    def _filtered_statement(
        self,
        query: DocumentListQuery,
        *,
        columns: tuple[Any, ...] = (documents_table,),
        include_document_type: bool = True,
        include_status: bool = True,
        visible_status: Any | None = None,
    ) -> Any:
        statement: Any = (
            select(*columns)
            .select_from(
                documents_table.join(
                    document_types_table,
                    documents_table.c.document_type_id == document_types_table.c.id,
                )
            )
            .where(document_is_not_deleting(documents_table.c.id))
        )
        if query.source is not None:
            statement = statement.where(documents_table.c.source == query.source)
        if query.connector is not None:
            statement = statement.where(documents_table.c.connector == query.connector)
        if query.archived is True:
            statement = statement.where(documents_table.c.status == DocumentStatus.APPROVED.value)
        elif query.archived is False:
            statement = statement.where(documents_table.c.status != DocumentStatus.APPROVED.value)
        if include_status and query.status is not None:
            statement = statement.where(
                (visible_status if visible_status is not None else _visible_status_expression())
                == query.status.value
            )
        if include_document_type and query.document_type_id is not None:
            statement = statement.where(
                documents_table.c.document_type_id == query.document_type_id
            )
        if query.search is not None:
            pattern = _contains_pattern(query.search)
            statement = statement.where(
                or_(
                    documents_table.c.name.ilike(pattern, escape="\\"),
                    documents_table.c.original_filename.ilike(pattern, escape="\\"),
                    document_types_table.c.name.ilike(pattern, escape="\\"),
                    document_types_table.c.external_id.ilike(pattern, escape="\\"),
                    documents_table.c.source.ilike(pattern, escape="\\"),
                    documents_table.c.connector.ilike(pattern, escape="\\"),
                    sql_cast(documents_table.c.document_type_id, String).ilike(
                        pattern, escape="\\"
                    ),
                )
            )
        return statement


def _document_ordering(query: DocumentListQuery, visible_status: Any) -> tuple[Any, Any]:
    return stable_order_by(
        sort_by=query.sort_by,
        direction=ListSortDirection(query.sort_order.value),
        allowlist={
            DocumentListSortField.CREATED: documents_table.c.created_at,
            DocumentListSortField.NAME: documents_table.c.name,
            DocumentListSortField.DOCUMENT_TYPE: document_types_table.c.name,
            DocumentListSortField.SOURCE: documents_table.c.source,
            DocumentListSortField.STATUS: visible_status,
            DocumentListSortField.SIZE: documents_table.c.content_size_bytes,
        },
        identity=documents_table.c.id,
    )


def _visible_status_expression() -> Any:
    """Return the status shown, filtered, faceted, and sorted in document lists."""

    latest_ocr_status = (
        select(ocr_pipeline_runs_table.c.status)
        .where(ocr_pipeline_runs_table.c.document_id == documents_table.c.id)
        .order_by(
            ocr_pipeline_runs_table.c.created_at.desc(),
            ocr_pipeline_runs_table.c.id.desc(),
        )
        .limit(1)
        .scalar_subquery()
    )
    return case(
        (latest_ocr_status == "failed", DocumentListStatus.FAILED.value),
        else_=documents_table.c.status,
    ).label("visible_status")


def _contains_pattern(value: str) -> str:
    """Escape SQL LIKE metacharacters before a case-insensitive contains search."""

    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


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
