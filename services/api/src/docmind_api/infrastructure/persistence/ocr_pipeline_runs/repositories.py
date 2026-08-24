"""OCR pipeline run repository implementations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.domain.documents.models import DocumentStatus
from docmind_api.domain.ocr_pipeline_runs.models import (
    OcrPipelineRunAcquireResult,
    OcrPipelineRunDocument,
    OcrPipelineRunExecutionAttempt,
    OcrPipelineRunExecutionLease,
    OcrPipelineRunList,
    OcrPipelineRunRecord,
    RunnableOcrPipelineSnapshot,
)
from docmind_api.domain.ocr_pipeline_runs.statuses import (
    ACTIVE_OCR_PIPELINE_RUN_STATUSES,
)
from docmind_api.infrastructure.persistence.documents.deletion_tables import (
    document_is_not_deleting,
)
from docmind_api.infrastructure.persistence.documents.tables import documents_table
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.execution_operations import (
    acquire_execution,
    fail_stale_executions,
    get_execution_attempt,
    mark_execution_invocation_started,
    record_execution_error,
    renew_execution,
    save_execution_result,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.mappers import (
    json_object,
    record_from_row,
    record_to_values,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.tables import (
    ocr_pipeline_runs_table,
)
from docmind_api.infrastructure.persistence.ocr_pipelines.tables import (
    ocr_pipeline_definition_versions_table,
    ocr_pipeline_definitions_table,
)

_ACTIVE_RUN_STATUS_VALUES = tuple(status.value for status in ACTIVE_OCR_PIPELINE_RUN_STATUSES)


class SqlAlchemyOcrPipelineRunDocumentReader:
    """PostgreSQL-backed document projection for OCR pipeline runs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_run_document(self, document_id: UUID) -> OcrPipelineRunDocument | None:
        """Return minimal document data needed to start a direct run."""

        result = await self._session.execute(
            select(
                documents_table.c.id,
                documents_table.c.document_type_id,
                documents_table.c.storage_locator,
                documents_table.c.content_size_bytes,
                documents_table.c.metadata_values,
                documents_table.c.status,
                documents_table.c.source,
                documents_table.c.connector,
                documents_table.c.connector_instance_id,
                documents_table.c.connector_correlation_id,
            )
            .where(
                documents_table.c.id == document_id,
                document_is_not_deleting(document_id),
            )
            .with_for_update(),
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        content_size = row["content_size_bytes"]
        return OcrPipelineRunDocument(
            id=row["id"],
            document_type_id=row["document_type_id"],
            storage_locator=str(row["storage_locator"]),
            content_size_bytes=int(content_size) if content_size is not None else None,
            metadata_values=json_object(row["metadata_values"]),
            is_archived=str(row["status"]) == DocumentStatus.APPROVED.value,
            source=str(row["source"]),
            connector=str(row["connector"]),
            connector_instance_id=row["connector_instance_id"],
            connector_correlation_id=row["connector_correlation_id"],
        )


class SqlAlchemyPublishedOcrPipelineSnapshotReader:
    """PostgreSQL-backed reader for the default published OCR pipeline snapshot."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_default_published(self) -> RunnableOcrPipelineSnapshot | None:
        """Return the active default published OCR pipeline snapshot."""

        statement = (
            select(
                ocr_pipeline_definitions_table.c.id,
                ocr_pipeline_definitions_table.c.display_name.label("pipeline_name"),
                ocr_pipeline_definitions_table.c.published_version,
                ocr_pipeline_definition_versions_table.c.compiled_snapshot,
                ocr_pipeline_definition_versions_table.c.catalog_version,
                ocr_pipeline_definition_versions_table.c.catalog_hash,
            )
            .join(
                ocr_pipeline_definition_versions_table,
                (
                    ocr_pipeline_definition_versions_table.c.definition_id
                    == ocr_pipeline_definitions_table.c.id
                )
                & (
                    ocr_pipeline_definition_versions_table.c.version_number
                    == ocr_pipeline_definitions_table.c.published_version
                ),
            )
            .where(
                ocr_pipeline_definitions_table.c.lifecycle == "published",
                ocr_pipeline_definitions_table.c.is_default.is_(True),
                ocr_pipeline_definitions_table.c.published_version.is_not(None),
                ocr_pipeline_definition_versions_table.c.status == "published",
                ocr_pipeline_definition_versions_table.c.compiled_snapshot.is_not(None),
            )
        )
        row = (await self._session.execute(statement)).mappings().one_or_none()
        if row is None:
            return None
        return RunnableOcrPipelineSnapshot(
            pipeline_id=row["id"],
            pipeline_version=int(row["published_version"]),
            compiled_snapshot=json_object(row["compiled_snapshot"]),
            catalog_version=row["catalog_version"],
            catalog_hash=row["catalog_hash"],
            pipeline_name=row["pipeline_name"],
        )


class SqlAlchemyOcrPipelineRunRepository:
    """PostgreSQL-backed OCR pipeline run repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: OcrPipelineRunRecord) -> bool:
        """Store a new OCR pipeline run."""

        statement = postgresql_insert(ocr_pipeline_runs_table).values(**record_to_values(record))
        result = await self._session.execute(
            statement.on_conflict_do_nothing().returning(ocr_pipeline_runs_table.c.id),
        )
        return result.scalar_one_or_none() is not None

    async def acquire_execution(
        self,
        run_id: UUID | str,
        *,
        attempt_id: UUID,
        owner_token: UUID,
        acquired_at: datetime,
        lease_expires_at: datetime,
        max_attempts: int,
    ) -> OcrPipelineRunAcquireResult | None:
        """Atomically acquire or observe one logical pipeline run."""

        normalized_id = _coerce_uuid(run_id)
        if normalized_id is None:
            return None
        return await acquire_execution(
            self._session,
            normalized_id,
            attempt_id=attempt_id,
            owner_token=owner_token,
            acquired_at=acquired_at,
            lease_expires_at=lease_expires_at,
            max_attempts=max_attempts,
        )

    async def renew_execution(
        self,
        lease: OcrPipelineRunExecutionLease,
        *,
        renewed_at: datetime,
        lease_expires_at: datetime,
    ) -> OcrPipelineRunExecutionLease | None:
        """Renew a current fenced owner lease."""

        return await renew_execution(
            self._session,
            lease,
            renewed_at=renewed_at,
            lease_expires_at=lease_expires_at,
        )

    async def save_execution_result(
        self,
        lease: OcrPipelineRunExecutionLease,
        record: OcrPipelineRunRecord,
        *,
        completed_at: datetime,
    ) -> bool:
        """Persist a result only for the current fenced owner."""

        return await save_execution_result(
            self._session,
            lease,
            record,
            completed_at=completed_at,
        )

    async def mark_execution_invocation_started(
        self,
        lease: OcrPipelineRunExecutionLease,
    ) -> bool:
        """Persist the no-takeover boundary before invoking LLM Magic."""

        return await mark_execution_invocation_started(
            self._session,
            lease,
        )

    async def record_execution_error(
        self,
        lease: OcrPipelineRunExecutionLease,
        *,
        error_code: str,
        updated_at: datetime,
    ) -> bool:
        """Persist a safe attempt error only for the current owner."""

        return await record_execution_error(
            self._session,
            lease,
            error_code=error_code,
            updated_at=updated_at,
        )

    async def fail_stale_executions(self, *, stale_after_seconds: float) -> int:
        """Fail logical runs whose execution owner has disappeared."""

        return await fail_stale_executions(
            self._session,
            stale_after_seconds=stale_after_seconds,
        )

    async def get_execution_attempt(
        self,
        attempt_id: UUID,
    ) -> OcrPipelineRunExecutionAttempt | None:
        """Return safe attempt history by physical attempt id."""

        return await get_execution_attempt(self._session, attempt_id)

    async def get_by_id(self, run_id: UUID | str) -> OcrPipelineRunRecord | None:
        """Return one OCR pipeline run by id."""

        normalized_id = _coerce_uuid(run_id)
        if normalized_id is None:
            return None
        result = await self._session.execute(
            _run_select().where(ocr_pipeline_runs_table.c.id == normalized_id),
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return record_from_row(row)

    async def get_active_by_document_id(
        self,
        document_id: UUID,
    ) -> OcrPipelineRunRecord | None:
        """Return the newest non-terminal run for one document, if one exists."""

        result = await self._session.execute(
            _run_select()
            .where(
                ocr_pipeline_runs_table.c.document_id == document_id,
                ocr_pipeline_runs_table.c.status.in_(_ACTIVE_RUN_STATUS_VALUES),
            )
            .order_by(
                ocr_pipeline_runs_table.c.created_at.desc(),
                ocr_pipeline_runs_table.c.id.desc(),
            )
            .limit(1),
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return record_from_row(row)

    async def list_by_document_id(
        self,
        document_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> OcrPipelineRunList:
        """Return runs for one document ordered newest first."""

        result = await self._session.execute(
            _run_select()
            .where(ocr_pipeline_runs_table.c.document_id == document_id)
            .order_by(
                ocr_pipeline_runs_table.c.created_at.desc(),
                ocr_pipeline_runs_table.c.id.desc(),
            )
            .limit(limit + 1)
            .offset(offset),
        )
        records = tuple(record_from_row(row) for row in result.mappings())
        return OcrPipelineRunList(
            runs=records[:limit],
            document_id=document_id,
            limit=limit,
            offset=offset,
            has_more=len(records) > limit,
        )


def _coerce_uuid(value: UUID | str) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _run_select():
    return select(
        ocr_pipeline_runs_table,
        ocr_pipeline_definitions_table.c.display_name.label("pipeline_name"),
    ).join(
        ocr_pipeline_definitions_table,
        ocr_pipeline_definitions_table.c.id == ocr_pipeline_runs_table.c.pipeline_id,
    )
