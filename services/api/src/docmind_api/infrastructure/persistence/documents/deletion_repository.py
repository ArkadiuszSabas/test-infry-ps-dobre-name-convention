"""PostgreSQL deletion fence and aggregate purge repository."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.documents.deletion_ports import DocumentDeletionRepository
from docmind_api.domain.documents.deletion import (
    DocumentDeletionFailureStage,
    DocumentDeletionOperation,
    DocumentDeletionStage,
)
from docmind_api.domain.documents.models import DocumentRecord
from docmind_api.infrastructure.persistence.connectors.document_archive_tables import (
    connector_document_archives_table,
)
from docmind_api.infrastructure.persistence.document_review.tables import (
    document_approval_decisions_table,
    document_approval_workflows_table,
    document_review_versions_table,
    document_reviews_table,
)
from docmind_api.infrastructure.persistence.documents.deletion_tables import (
    document_deletion_operations_table,
)
from docmind_api.infrastructure.persistence.documents.repositories import (
    document_from_row,
)
from docmind_api.infrastructure.persistence.documents.tables import (
    document_type_change_audit_events_table,
    documents_table,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.tables import (
    ocr_pipeline_runs_table,
)
from docmind_core.connectors import (
    ConnectorDocumentDeletionPolicy,
    ConnectorDocumentDeletionResult,
)


class SqlAlchemyDocumentDeletionRepository(DocumentDeletionRepository):
    """Persist the fence independently from the aggregate it ultimately removes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, document_id: UUID) -> DocumentDeletionOperation | None:
        result = await self._session.execute(
            select(document_deletion_operations_table).where(
                document_deletion_operations_table.c.document_id == document_id
            )
        )
        row = result.mappings().one_or_none()
        return _operation_from_row(row) if row is not None else None

    async def get_document(self, document_id: UUID) -> DocumentRecord | None:
        result = await self._session.execute(
            select(documents_table).where(documents_table.c.id == document_id)
        )
        row = result.mappings().one_or_none()
        return document_from_row(row) if row is not None else None

    async def reserve(self, document: DocumentRecord) -> DocumentDeletionOperation:
        await self._session.execute(
            select(documents_table.c.id)
            .where(documents_table.c.id == document.id)
            .with_for_update()
        )
        now = datetime.now(tz=UTC)
        await self._session.execute(
            postgresql_insert(document_deletion_operations_table)
            .values(
                document_id=document.id,
                operation_id=uuid4(),
                stage=DocumentDeletionStage.REQUESTED.value,
                connector_instance_id=document.source.connector_instance_id,
                policy=None,
                warning_code=None,
                failure_stage=None,
                error_code=None,
                created_at=now,
                updated_at=now,
                completed_at=None,
            )
            .on_conflict_do_nothing(
                index_elements=[document_deletion_operations_table.c.document_id]
            )
        )
        operation = await self.get(document.id)
        if operation is None:
            raise RuntimeError("Document deletion fence was not persisted.")
        return operation

    async def advance(
        self,
        document_id: UUID,
        *,
        stage: DocumentDeletionStage,
        connector_result: ConnectorDocumentDeletionResult | None = None,
    ) -> DocumentDeletionOperation:
        values: dict[str, object] = {
            "stage": stage.value,
            "failure_stage": None,
            "error_code": None,
            "updated_at": datetime.now(tz=UTC),
        }
        if connector_result is not None:
            values["policy"] = connector_result.policy.value
            values["warning_code"] = connector_result.warning_code
        previous_stage = {
            DocumentDeletionStage.CONNECTOR_PREPARED: DocumentDeletionStage.REQUESTED,
            DocumentDeletionStage.CONTENT_DELETED: DocumentDeletionStage.CONNECTOR_PREPARED,
        }.get(stage)
        if previous_stage is None:
            raise RuntimeError("Unsupported document deletion stage transition.")
        await self._session.execute(
            update(document_deletion_operations_table)
            .where(
                document_deletion_operations_table.c.document_id == document_id,
                document_deletion_operations_table.c.stage == previous_stage.value,
            )
            .values(**values)
        )
        return await self._require(document_id)

    async def fail(
        self,
        document_id: UUID,
        *,
        failure_stage: DocumentDeletionFailureStage,
        error_code: str,
        connector_result: ConnectorDocumentDeletionResult | None = None,
    ) -> DocumentDeletionOperation:
        values: dict[str, object] = {
            "failure_stage": failure_stage.value,
            "error_code": error_code,
            "updated_at": datetime.now(tz=UTC),
        }
        if connector_result is not None:
            values["policy"] = connector_result.policy.value
            values["warning_code"] = connector_result.warning_code
        await self._session.execute(
            update(document_deletion_operations_table)
            .where(
                document_deletion_operations_table.c.document_id == document_id,
                document_deletion_operations_table.c.stage != DocumentDeletionStage.COMPLETED.value,
            )
            .values(**values)
        )
        return await self._require(document_id)

    async def purge(self, document_id: UUID) -> DocumentDeletionOperation:
        operation = await self._require_for_update(document_id)
        if operation.stage is DocumentDeletionStage.COMPLETED:
            return operation
        if operation.stage is not DocumentDeletionStage.CONTENT_DELETED:
            raise RuntimeError("Document aggregate purge requires deleted content.")

        review_ids = select(document_reviews_table.c.id).where(
            document_reviews_table.c.document_id == document_id
        )
        await self._session.execute(
            delete(document_approval_decisions_table).where(
                document_approval_decisions_table.c.document_id == document_id
            )
        )
        await self._session.execute(
            delete(document_approval_workflows_table).where(
                document_approval_workflows_table.c.document_id == document_id
            )
        )
        await self._session.execute(
            delete(document_review_versions_table).where(
                document_review_versions_table.c.review_id.in_(review_ids)
            )
        )
        await self._session.execute(
            delete(document_reviews_table).where(
                document_reviews_table.c.document_id == document_id
            )
        )
        await self._session.execute(
            delete(connector_document_archives_table).where(
                connector_document_archives_table.c.document_id == document_id
            )
        )
        await self._session.execute(
            delete(document_type_change_audit_events_table).where(
                document_type_change_audit_events_table.c.document_id == document_id
            )
        )
        await self._session.execute(
            delete(ocr_pipeline_runs_table).where(
                ocr_pipeline_runs_table.c.document_id == document_id
            )
        )
        result = await self._session.execute(
            delete(documents_table)
            .where(documents_table.c.id == document_id)
            .returning(documents_table.c.id)
        )
        if result.scalar_one_or_none() is None:
            raise RuntimeError("Document disappeared before aggregate purge completed.")

        completed_at = datetime.now(tz=UTC)
        await self._session.execute(
            update(document_deletion_operations_table)
            .where(document_deletion_operations_table.c.document_id == document_id)
            .values(
                stage=DocumentDeletionStage.COMPLETED.value,
                failure_stage=None,
                error_code=None,
                updated_at=completed_at,
                completed_at=completed_at,
            )
        )
        return await self._require(document_id)

    async def _require(self, document_id: UUID) -> DocumentDeletionOperation:
        operation = await self.get(document_id)
        if operation is None:
            raise RuntimeError("Document deletion operation was not found.")
        return operation

    async def _require_for_update(self, document_id: UUID) -> DocumentDeletionOperation:
        result = await self._session.execute(
            select(document_deletion_operations_table)
            .where(document_deletion_operations_table.c.document_id == document_id)
            .with_for_update()
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise RuntimeError("Document deletion operation was not found.")
        return _operation_from_row(row)


def _operation_from_row(row: Mapping[Any, Any]) -> DocumentDeletionOperation:
    return DocumentDeletionOperation(
        operation_id=row["operation_id"],
        document_id=row["document_id"],
        stage=DocumentDeletionStage(str(row["stage"])),
        connector_instance_id=row["connector_instance_id"],
        policy=(
            ConnectorDocumentDeletionPolicy(str(row["policy"]))
            if row["policy"] is not None
            else None
        ),
        warning_code=row["warning_code"],
        failure_stage=(
            DocumentDeletionFailureStage(str(row["failure_stage"]))
            if row["failure_stage"] is not None
            else None
        ),
        error_code=row["error_code"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )
