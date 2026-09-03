"""OCR pipeline run repository implementations."""

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.ocr_pipeline_runs.ports import (
    OcrCancellationResult,
    OcrEventCompletion,
    OcrEventDispatchResult,
    OcrRunOutboxRecord,
)
from docmind_api.domain.documents.models import DocumentStatus
from docmind_api.domain.ocr_pipeline_runs.models import (
    OcrPipelineRunActorType,
    OcrPipelineRunDocument,
    OcrPipelineRunList,
    OcrPipelineRunRecord,
    OcrPipelineRunStatus,
    RunnableOcrPipelineSnapshot,
)
from docmind_api.domain.ocr_pipeline_runs.statuses import (
    ACTIVE_OCR_PIPELINE_RUN_STATUSES,
)
from docmind_api.infrastructure.ocr_pipeline_runs.metrics import (
    OcrAdmissionSnapshot,
    record_ocr_admission_deferral,
    record_ocr_reservation_expiration,
    update_ocr_admission_snapshot,
)
from docmind_api.infrastructure.persistence.documents.deletion_tables import (
    document_is_not_deleting,
)
from docmind_api.infrastructure.persistence.documents.tables import documents_table
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.execution_mapping import (
    mutable_run_values,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.mappers import (
    json_object,
    record_from_row,
    record_to_values,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.tables import (
    ocr_pipeline_run_attempts_table,
    ocr_pipeline_run_capacity_lock_table,
    ocr_pipeline_run_outbox_table,
    ocr_pipeline_runs_table,
)
from docmind_api.infrastructure.persistence.ocr_pipelines.tables import (
    ocr_pipeline_definition_versions_table,
    ocr_pipeline_definitions_table,
)
from docmind_core.ocr_pipeline.contracts import (
    OCR_DOCUMENT_PROCESSING_TOPIC,
    OCR_RUN_CANCELLATION_REQUESTED_EVENT_TYPE,
    OCR_RUN_REQUESTED_EVENT_TYPE,
    OcrPipelineEventV1,
    OcrRunCancellationRequestedV1,
    OcrRunRequestedV1,
)

_ACTIVE_RUN_STATUS_VALUES = tuple(status.value for status in ACTIVE_OCR_PIPELINE_RUN_STATUSES)


class SqlAlchemyOcrPipelineRunDocumentReader:
    """PostgreSQL-backed document projection for OCR pipeline runs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_run_document(self, document_id: UUID) -> OcrPipelineRunDocument | None:
        """Return minimal document data needed to start an OCR run."""

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
    """PostgreSQL-backed reader for active published OCR pipeline snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_default_published(self) -> RunnableOcrPipelineSnapshot | None:
        """Return the active default published OCR pipeline snapshot."""

        pipelines = await self._list_published(default_only=True)
        return pipelines[0] if pipelines else None

    async def get_published(
        self,
        pipeline_id: UUID,
    ) -> RunnableOcrPipelineSnapshot | None:
        """Return one active published OCR pipeline snapshot by id."""

        pipelines = await self._list_published(pipeline_id=pipeline_id)
        return pipelines[0] if pipelines else None

    async def list_published(self) -> tuple[RunnableOcrPipelineSnapshot, ...]:
        """Return active published OCR pipeline snapshots for run selection."""

        return await self._list_published()

    async def _list_published(
        self,
        *,
        pipeline_id: UUID | None = None,
        default_only: bool = False,
    ) -> tuple[RunnableOcrPipelineSnapshot, ...]:
        statement = (
            select(
                ocr_pipeline_definitions_table.c.id,
                ocr_pipeline_definitions_table.c.display_name.label("pipeline_name"),
                ocr_pipeline_definitions_table.c.is_default,
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
                ocr_pipeline_definitions_table.c.published_version.is_not(None),
                ocr_pipeline_definition_versions_table.c.status == "published",
                ocr_pipeline_definition_versions_table.c.compiled_snapshot.is_not(None),
            )
            .order_by(
                ocr_pipeline_definitions_table.c.is_default.desc(),
                ocr_pipeline_definitions_table.c.display_name.asc(),
                ocr_pipeline_definitions_table.c.id.asc(),
            )
        )
        if pipeline_id is not None:
            statement = statement.where(ocr_pipeline_definitions_table.c.id == pipeline_id)
        if default_only:
            statement = statement.where(ocr_pipeline_definitions_table.c.is_default.is_(True))
        rows = (await self._session.execute(statement)).mappings().all()
        return tuple(
            RunnableOcrPipelineSnapshot(
                pipeline_id=row["id"],
                pipeline_version=int(row["published_version"]),
                compiled_snapshot=json_object(row["compiled_snapshot"]),
                catalog_version=row["catalog_version"],
                catalog_hash=row["catalog_hash"],
                pipeline_name=row["pipeline_name"],
                is_default=bool(row["is_default"]),
            )
            for row in rows
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

    async def add_request_outbox(self, record: OcrPipelineRunRecord) -> None:
        """Store the stable run-request event in the same transaction as its run."""

        event = OcrRunRequestedV1(
            run_id=str(record.id),
            document_id=str(record.document_id),
            correlation_id=str(record.id),
            requested_at=record.created_at.astimezone(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        )
        await self._session.execute(
            postgresql_insert(ocr_pipeline_run_outbox_table).values(
                id=uuid4(),
                run_id=record.id,
                topic=OCR_DOCUMENT_PROCESSING_TOPIC,
                event_type=OCR_RUN_REQUESTED_EVENT_TYPE,
                payload=event.model_dump(mode="json"),
                created_at=record.created_at,
                available_at=record.created_at,
                dedupe_key=None,
            )
        )

    async def claim_request_outbox(self, *, limit: int) -> tuple[OcrRunOutboxRecord, ...]:
        """Claim pending requests without deleting them, preserving at-least-once delivery."""

        if limit < 1:
            return ()
        rows = (
            (
                await self._session.execute(
                    select(ocr_pipeline_run_outbox_table)
                    .where(
                        ocr_pipeline_run_outbox_table.c.published_at.is_(None),
                        ocr_pipeline_run_outbox_table.c.available_at <= func.clock_timestamp(),
                    )
                    .order_by(
                        ocr_pipeline_run_outbox_table.c.available_at,
                        ocr_pipeline_run_outbox_table.c.created_at,
                    )
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            )
            .mappings()
            .all()
        )
        claimed: list[OcrRunOutboxRecord] = []
        for row in rows:
            await self._session.execute(
                ocr_pipeline_run_outbox_table.update()
                .where(ocr_pipeline_run_outbox_table.c.id == row["id"])
                .values(
                    publish_attempts=ocr_pipeline_run_outbox_table.c.publish_attempts + 1,
                )
            )
            claimed.append(
                OcrRunOutboxRecord(
                    id=row["id"],
                    topic=str(row["topic"]),
                    event_type=str(row["event_type"]),
                    payload=dict(row["payload"]),
                    publish_attempts=int(row["publish_attempts"]) + 1,
                )
            )
        return tuple(claimed)

    async def mark_request_outbox_published(
        self,
        outbox_id: UUID,
        *,
        published_at: datetime,
    ) -> bool:
        """Mark a request published only after Dapr confirms success."""

        result = await self._session.execute(
            ocr_pipeline_run_outbox_table.update()
            .where(
                ocr_pipeline_run_outbox_table.c.id == outbox_id,
                ocr_pipeline_run_outbox_table.c.published_at.is_(None),
            )
            .values(published_at=published_at)
            .returning(ocr_pipeline_run_outbox_table.c.id)
        )
        return result.scalar_one_or_none() is not None

    async def dispatch_event_run(
        self,
        run_id: UUID,
        *,
        attempt_id: UUID,
        owner_token: UUID,
        max_concurrency: int,
        reservation_timeout_seconds: float,
        execution_timeout_seconds: float,
        defer_seconds: float,
    ) -> OcrEventDispatchResult | None:
        """Atomically reserve one global slot or schedule one durable redispatch."""

        if max_concurrency < 1:
            raise ValueError("OCR pipeline max concurrency must be positive.")
        await self._lock_capacity()
        latest = await self._latest_attempt(run_id, lock=True)
        run_row = (
            (
                await self._session.execute(
                    select(ocr_pipeline_runs_table)
                    .where(ocr_pipeline_runs_table.c.id == run_id)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if run_row is None:
            return None
        record = record_from_row(run_row)
        if record.is_terminal:
            return OcrEventDispatchResult(disposition="terminal")
        if record.status is OcrPipelineRunStatus.CANCELLING:
            return OcrEventDispatchResult(disposition="active")

        now = (await self._session.execute(select(func.clock_timestamp()))).scalar_one()
        if latest is not None and str(latest["status"]) == "running":
            return OcrEventDispatchResult(disposition="active")
        if latest is not None and str(latest["status"]) == "reserved":
            if cast(datetime, latest["lease_expires_at"]) > now:
                return self._dispatchable_result(record, latest)
            await self._finish_attempt(
                latest,
                status="lost",
                error_code="OCR_PIPELINE_RESERVATION_EXPIRED",
                completed_at=now,
            )

        active_count = int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(ocr_pipeline_run_attempts_table)
                    .where(ocr_pipeline_run_attempts_table.c.status.in_(("reserved", "running")))
                )
            ).scalar_one()
        )
        if active_count >= max_concurrency:
            await self._enqueue_delayed_request(
                record,
                available_at=now + timedelta(seconds=defer_seconds),
            )
            return OcrEventDispatchResult(disposition="deferred")

        attempt_number = int(cast(int, latest["attempt_number"])) + 1 if latest is not None else 1
        reservation_deadline = now + timedelta(seconds=reservation_timeout_seconds)
        execution_deadline = now + timedelta(seconds=execution_timeout_seconds)
        await self._session.execute(
            ocr_pipeline_run_attempts_table.insert().values(
                attempt_id=attempt_id,
                run_id=run_id,
                owner_token=owner_token,
                attempt_number=attempt_number,
                fencing_token=attempt_number,
                status="reserved",
                started_at=now,
                invocation_started_at=None,
                last_renewed_at=now,
                lease_expires_at=reservation_deadline,
                completed_at=None,
                error_code=None,
                execution_deadline_at=execution_deadline,
                last_event_sequence=0,
            )
        )
        return OcrEventDispatchResult(
            disposition="dispatchable",
            attempt_id=attempt_id,
            attempt_number=attempt_number,
            fencing_token=attempt_number,
            execution_deadline_at=execution_deadline,
            run_request=_event_run_request(
                record,
                attempt_id=attempt_id,
                attempt_number=attempt_number,
                fencing_token=attempt_number,
            ),
        )

    async def defer_event_dispatch(
        self,
        run_id: UUID,
        attempt_id: UUID,
        *,
        fencing_token: int,
        defer_seconds: float,
    ) -> bool:
        """Release a local-capacity rejection and schedule one durable redispatch."""

        await self._lock_capacity()
        now = (await self._session.execute(select(func.clock_timestamp()))).scalar_one()
        attempt = await self._current_attempt(run_id, attempt_id, fencing_token)
        if attempt is None:
            return False
        if str(attempt["status"]) == "lost":
            return True
        if str(attempt["status"]) != "reserved":
            return False
        await self._finish_attempt(
            attempt,
            status="lost",
            error_code="OCR_PIPELINE_LOCAL_CAPACITY_REJECTED",
            completed_at=now,
        )
        record = await self.get_by_id(run_id)
        if record is not None and not record.is_terminal:
            await self._enqueue_delayed_request(
                record,
                available_at=now + timedelta(seconds=defer_seconds),
            )
        return True

    async def fail_event_dispatch(
        self,
        run_id: UUID,
        attempt_id: UUID,
        *,
        fencing_token: int,
        error_code: str,
    ) -> bool:
        """Fail only the current non-terminal attempt with the supplied fence."""

        await self._lock_capacity()
        attempt = await self._current_attempt(run_id, attempt_id, fencing_token)
        if attempt is None or str(attempt["status"]) != "reserved":
            return False
        run = (
            (
                await self._session.execute(
                    select(ocr_pipeline_runs_table)
                    .where(ocr_pipeline_runs_table.c.id == run_id)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if run is None or str(run["status"]) not in {"pending", "running"}:
            return False
        now = (await self._session.execute(select(func.clock_timestamp()))).scalar_one()
        await self._finish_attempt(
            attempt,
            status="failed",
            error_code=error_code,
            completed_at=now,
        )
        await self._session.execute(
            update(ocr_pipeline_runs_table)
            .where(ocr_pipeline_runs_table.c.id == run_id)
            .values(
                status="failed",
                error={"code": error_code, "message": "OCR pipeline dispatch was rejected."},
                started_at=func.coalesce(ocr_pipeline_runs_table.c.started_at, now),
                completed_at=now,
                updated_at=now,
            )
        )
        return True

    async def apply_pipeline_event(self, event: OcrPipelineEventV1) -> str:
        """Apply only a current, strictly newer event sequence."""

        from sqlalchemy import and_

        attempt = (
            (
                await self._session.execute(
                    select(ocr_pipeline_run_attempts_table)
                    .where(
                        ocr_pipeline_run_attempts_table.c.attempt_id == UUID(event.attempt_id),
                        ocr_pipeline_run_attempts_table.c.run_id == UUID(event.run_id),
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if attempt is None:
            return "deleted"
        run = (
            (
                await self._session.execute(
                    select(ocr_pipeline_runs_table)
                    .where(ocr_pipeline_runs_table.c.id == UUID(event.run_id))
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if run is None:
            return "deleted"
        latest_attempt = (
            (
                await self._session.execute(
                    select(ocr_pipeline_run_attempts_table)
                    .where(ocr_pipeline_run_attempts_table.c.run_id == UUID(event.run_id))
                    .order_by(ocr_pipeline_run_attempts_table.c.attempt_number.desc())
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        if latest_attempt is None:
            return "deleted"
        if latest_attempt["attempt_id"] != UUID(event.attempt_id):
            return "stale"
        if str(latest_attempt["status"]) not in {"reserved", "running"}:
            return "stale"
        if int(attempt["fencing_token"]) != event.fencing_token:
            return "stale"
        if cast(UUID, run["document_id"]) != UUID(event.document_id) or cast(
            UUID, run["pipeline_id"]
        ) != UUID(event.pipeline_id):
            return "stale"
        if str(run["status"]) not in ("pending", "running"):
            return "terminal"
        last_sequence = int(attempt.get("last_event_sequence") or 0)
        if event.sequence <= last_sequence:
            return "duplicate"
        steps = [
            {
                "step_id": step.step_id,
                "step_type": step.step_type,
                "implementation_id": step.implementation_id,
                "display_name": step.display_name,
                "status": step.status.value,
                "duration_seconds": (
                    step.duration_ms / 1000 if step.duration_ms is not None else None
                ),
                "metrics": dict(step.metrics),
                "error": step.error.model_dump(mode="json") if step.error else None,
            }
            for step in event.steps
        ]
        await self._session.execute(
            ocr_pipeline_run_attempts_table.update()
            .where(
                and_(
                    ocr_pipeline_run_attempts_table.c.attempt_id == UUID(event.attempt_id),
                    ocr_pipeline_run_attempts_table.c.last_event_sequence < event.sequence,
                )
            )
            .values(last_event_sequence=event.sequence)
        )
        if event.kind.value in ("pipeline.started", "pipeline.step.completed"):
            fenced_metrics = dict(cast(dict[str, object], run["metrics"]))
            fenced_metrics["execution_attempt_count"] = int(attempt["attempt_number"])
            fenced_started_at = (
                select(ocr_pipeline_run_attempts_table.c.started_at)
                .where(ocr_pipeline_run_attempts_table.c.attempt_id == UUID(event.attempt_id))
                .scalar_subquery()
            )
            await self._session.execute(
                ocr_pipeline_run_attempts_table.update()
                .where(
                    ocr_pipeline_run_attempts_table.c.attempt_id == UUID(event.attempt_id),
                    ocr_pipeline_run_attempts_table.c.status == "reserved",
                )
                .values(
                    status="running",
                    invocation_started_at=func.coalesce(
                        ocr_pipeline_run_attempts_table.c.invocation_started_at,
                        func.clock_timestamp(),
                    ),
                    lease_expires_at=ocr_pipeline_run_attempts_table.c.execution_deadline_at,
                    last_renewed_at=func.clock_timestamp(),
                )
            )
            await self._session.execute(
                ocr_pipeline_runs_table.update()
                .where(ocr_pipeline_runs_table.c.id == UUID(event.run_id))
                .values(
                    status="running",
                    steps=steps,
                    metrics=fenced_metrics,
                    started_at=func.coalesce(
                        ocr_pipeline_runs_table.c.started_at,
                        fenced_started_at,
                    ),
                    updated_at=fenced_started_at,
                )
            )
        return "applied"

    async def complete_event_run(
        self,
        run_id: UUID,
        attempt_id: UUID,
        completion: OcrEventCompletion,
    ) -> str:
        """Atomically persist one current, in-deadline terminal result."""

        attempt = (
            (
                await self._session.execute(
                    select(ocr_pipeline_run_attempts_table)
                    .where(
                        ocr_pipeline_run_attempts_table.c.attempt_id == attempt_id,
                        ocr_pipeline_run_attempts_table.c.run_id == run_id,
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        run = (
            (
                await self._session.execute(
                    select(ocr_pipeline_runs_table)
                    .where(ocr_pipeline_runs_table.c.id == run_id)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if attempt is None or run is None:
            return "deleted"
        if UUID(str(run["document_id"])) != completion.document_id:
            return "stale"
        if int(attempt["fencing_token"]) != completion.fencing_token:
            return "stale"
        if str(run["status"]) in {"succeeded", "partial_failed", "failed", "cancelled"}:
            return "duplicate" if str(attempt["status"]) == completion.status.value else "stale"
        if str(run["status"]) == "cancelling":
            return "stale"
        if str(attempt["status"]) not in {"reserved", "running"}:
            return "stale"
        deadline = attempt["execution_deadline_at"]
        now = (await self._session.execute(select(func.clock_timestamp()))).scalar_one()
        if deadline is None or deadline <= now:
            return "expired"

        persisted = replace(
            record_from_row(run),
            status=completion.status,
            steps=completion.steps,
            metrics=completion.metrics,
            diagnostics=completion.diagnostics,
            error=completion.error,
            result_payload=completion.result_payload,
            started_at=record_from_row(run).started_at or attempt["started_at"],
            completed_at=now,
            updated_at=now,
        )
        attempt_result = await self._session.execute(
            update(ocr_pipeline_run_attempts_table)
            .where(
                ocr_pipeline_run_attempts_table.c.attempt_id == attempt_id,
                ocr_pipeline_run_attempts_table.c.run_id == run_id,
                ocr_pipeline_run_attempts_table.c.fencing_token == completion.fencing_token,
                ocr_pipeline_run_attempts_table.c.status.in_(("reserved", "running")),
            )
            .values(
                status=completion.status.value,
                completed_at=now,
                error_code=completion.error.code if completion.error is not None else None,
            )
            .returning(ocr_pipeline_run_attempts_table.c.attempt_id)
        )
        if attempt_result.scalar_one_or_none() is None:
            return "stale"
        await self._session.execute(
            update(ocr_pipeline_runs_table)
            .where(
                ocr_pipeline_runs_table.c.id == run_id,
                ocr_pipeline_runs_table.c.status.in_(("pending", "running")),
            )
            .values(**mutable_run_values(persisted))
        )
        return "completed"

    async def reconcile_event_executions(self, *, defer_seconds: float) -> int:
        """Recover expired reservations and fail runs past their execution deadline."""

        await self._lock_capacity()
        now = (await self._session.execute(select(func.clock_timestamp()))).scalar_one()
        rows = (
            (
                await self._session.execute(
                    select(ocr_pipeline_run_attempts_table)
                    .join(
                        ocr_pipeline_runs_table,
                        ocr_pipeline_runs_table.c.id == ocr_pipeline_run_attempts_table.c.run_id,
                    )
                    .where(
                        ocr_pipeline_runs_table.c.status.in_(("pending", "running")),
                        (
                            (ocr_pipeline_run_attempts_table.c.status == "reserved")
                            & (ocr_pipeline_run_attempts_table.c.lease_expires_at <= now)
                        )
                        | (
                            (ocr_pipeline_run_attempts_table.c.status == "running")
                            & (ocr_pipeline_run_attempts_table.c.execution_deadline_at <= now)
                        ),
                    )
                    .with_for_update(skip_locked=True)
                )
            )
            .mappings()
            .all()
        )
        reconciled = 0
        for row in rows:
            run_id = cast(UUID, row["run_id"])
            if str(row["status"]) == "reserved":
                await self._finish_attempt(
                    dict(row),
                    status="lost",
                    error_code="OCR_PIPELINE_RESERVATION_EXPIRED",
                    completed_at=now,
                )
                record_ocr_reservation_expiration()
                record = await self.get_by_id(run_id)
                if record is not None and not record.is_terminal:
                    await self._enqueue_delayed_request(
                        record,
                        available_at=now + timedelta(seconds=defer_seconds),
                    )
            else:
                await self._finish_attempt(
                    dict(row),
                    status="failed",
                    error_code="OCR_PIPELINE_EXECUTION_DEADLINE_EXCEEDED",
                    completed_at=now,
                )
                await self._session.execute(
                    update(ocr_pipeline_runs_table)
                    .where(
                        ocr_pipeline_runs_table.c.id == run_id,
                        ocr_pipeline_runs_table.c.status.in_(("pending", "running")),
                    )
                    .values(
                        status="failed",
                        error={
                            "code": "OCR_PIPELINE_EXECUTION_DEADLINE_EXCEEDED",
                            "message": "OCR pipeline execution deadline was exceeded.",
                        },
                        completed_at=now,
                        updated_at=now,
                    )
                )
            reconciled += 1
        return reconciled

    async def refresh_admission_metrics(self) -> OcrAdmissionSnapshot:
        """Refresh safe process-local gauges from durable database state."""

        now = (await self._session.execute(select(func.clock_timestamp()))).scalar_one()
        waiting_filter = (
            (ocr_pipeline_run_outbox_table.c.published_at.is_(None))
            & (ocr_pipeline_run_outbox_table.c.event_type == OCR_RUN_REQUESTED_EVENT_TYPE)
            & (ocr_pipeline_run_outbox_table.c.dedupe_key.is_not(None))
        )
        waiting_row = (
            await self._session.execute(
                select(
                    func.count(func.distinct(ocr_pipeline_run_outbox_table.c.run_id)),
                    func.min(ocr_pipeline_run_outbox_table.c.created_at),
                ).where(waiting_filter)
            )
        ).one()
        lease_counts = (
            await self._session.execute(
                select(
                    func.count().filter(ocr_pipeline_run_attempts_table.c.status == "reserved"),
                    func.count().filter(ocr_pipeline_run_attempts_table.c.status == "running"),
                )
            )
        ).one()
        oldest_created_at = cast(datetime | None, waiting_row[1])
        snapshot = OcrAdmissionSnapshot(
            waiting_runs=int(waiting_row[0]),
            oldest_waiting_age_seconds=(
                max(0.0, (now - oldest_created_at).total_seconds())
                if oldest_created_at is not None
                else 0.0
            ),
            reserved_leases=int(lease_counts[0]),
            running_leases=int(lease_counts[1]),
        )
        update_ocr_admission_snapshot(snapshot)
        return snapshot

    async def request_cancellation(
        self,
        run_id: UUID,
        *,
        actor_id: str,
        actor_login: str | None,
        cancellation_timeout_seconds: float,
    ) -> OcrCancellationResult | None:
        """Cancel an unstarted run or durably command its current execution to stop."""

        await self._lock_capacity()
        latest = await self._latest_attempt(run_id, lock=True)
        run = (
            (
                await self._session.execute(
                    select(ocr_pipeline_runs_table)
                    .where(ocr_pipeline_runs_table.c.id == run_id)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if run is None:
            return None
        record = record_from_row(run)
        if record.is_terminal:
            return OcrCancellationResult(disposition="terminal", record=record)
        if record.status.value == "cancelling":
            return OcrCancellationResult(disposition="cancelling", record=record)

        now = (await self._session.execute(select(func.clock_timestamp()))).scalar_one()
        await self._invalidate_pending_run_requests(run_id, published_at=now)
        if latest is None or str(latest["status"]) in {"lost", "failed", "indeterminate"}:
            await self._terminalize_cancelled_run(
                run_id,
                requested_at=now,
                actor_id=actor_id,
                actor_login=actor_login,
            )
            cancelled = await self.get_by_id(run_id)
            if cancelled is None:
                return None
            return OcrCancellationResult(disposition="cancelled", record=cancelled)

        if str(latest["status"]) == "reserved":
            await self._finish_attempt(
                latest,
                status="cancelled",
                error_code="OCR_PIPELINE_RUN_CANCELLED",
                completed_at=now,
            )
            await self._terminalize_cancelled_run(
                run_id,
                requested_at=now,
                actor_id=actor_id,
                actor_login=actor_login,
            )
            await self._enqueue_cancellation_command(
                record,
                latest,
                requested_at=now,
            )
            cancelled = await self.get_by_id(run_id)
            if cancelled is None:
                return None
            return OcrCancellationResult(disposition="cancelled", record=cancelled)

        if str(latest["status"]) != "running":
            return OcrCancellationResult(disposition="active", record=record)
        deadline = now + timedelta(seconds=cancellation_timeout_seconds)
        await self._session.execute(
            update(ocr_pipeline_runs_table)
            .where(
                ocr_pipeline_runs_table.c.id == run_id,
                ocr_pipeline_runs_table.c.status.in_(("pending", "running")),
            )
            .values(
                status="cancelling",
                cancellation_requested_at=now,
                cancellation_requested_by_actor_id=actor_id,
                cancellation_requested_by_actor_login=actor_login,
                updated_at=now,
            )
        )
        await self._session.execute(
            update(ocr_pipeline_run_attempts_table)
            .where(ocr_pipeline_run_attempts_table.c.attempt_id == latest["attempt_id"])
            .values(cancellation_deadline_at=deadline)
        )
        await self._enqueue_cancellation_command(
            record,
            latest,
            requested_at=now,
        )
        cancelling = await self.get_by_id(run_id)
        if cancelling is None:
            return None
        return OcrCancellationResult(disposition="cancelling", record=cancelling)

    async def complete_cancellation(
        self,
        run_id: UUID,
        attempt_id: UUID,
        *,
        fencing_token: int,
        error_code: str | None = None,
    ) -> str:
        """Apply the first terminal cancellation for the current fenced attempt."""

        await self._lock_capacity()
        attempt = await self._current_attempt(run_id, attempt_id, fencing_token)
        run = (
            (
                await self._session.execute(
                    select(ocr_pipeline_runs_table)
                    .where(ocr_pipeline_runs_table.c.id == run_id)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if attempt is None or run is None:
            return "deleted"
        if str(run["status"]) == "cancelled":
            return "duplicate"
        if str(run["status"]) != "cancelling" or str(attempt["status"]) != "running":
            return "stale"
        now = (await self._session.execute(select(func.clock_timestamp()))).scalar_one()
        diagnostics = list(cast(list[dict[str, object]], run["diagnostics"]))
        if error_code is not None:
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": error_code,
                    "message": "OCR pipeline cancellation could not be confirmed.",
                    "step_id": None,
                    "path": None,
                }
            )
        await self._finish_attempt(
            attempt,
            status="cancelled",
            error_code=error_code or "OCR_PIPELINE_RUN_CANCELLED",
            completed_at=now,
        )
        await self._session.execute(
            update(ocr_pipeline_runs_table)
            .where(
                ocr_pipeline_runs_table.c.id == run_id,
                ocr_pipeline_runs_table.c.status == "cancelling",
            )
            .values(
                status="cancelled",
                started_at=func.coalesce(ocr_pipeline_runs_table.c.started_at, now),
                diagnostics=diagnostics,
                error=(
                    {"code": error_code, "message": "OCR cancellation was not confirmed."}
                    if error_code is not None
                    else None
                ),
                completed_at=now,
                updated_at=now,
            )
        )
        return "cancelled"

    async def record_cancellation_dispatch_failure(
        self,
        run_id: UUID,
        attempt_id: UUID,
        *,
        fencing_token: int,
        error_code: str,
    ) -> str:
        """Persist a safe diagnostic while the cancellation watchdog remains authoritative."""

        await self._lock_capacity()
        attempt = await self._current_attempt(run_id, attempt_id, fencing_token)
        run = (
            (
                await self._session.execute(
                    select(ocr_pipeline_runs_table)
                    .where(ocr_pipeline_runs_table.c.id == run_id)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if attempt is None or run is None:
            return "deleted"
        if str(run["status"]) == "cancelled":
            return "duplicate"
        if str(run["status"]) != "cancelling" or str(attempt["status"]) != "running":
            return "stale"
        diagnostics = list(cast(list[dict[str, object]], run["diagnostics"]))
        if not any(diagnostic.get("code") == error_code for diagnostic in diagnostics):
            diagnostics.append(
                {
                    "severity": "warning",
                    "code": error_code,
                    "message": "OCR pipeline cancellation dispatch was rejected.",
                    "step_id": None,
                    "path": None,
                }
            )
            await self._session.execute(
                update(ocr_pipeline_runs_table)
                .where(
                    ocr_pipeline_runs_table.c.id == run_id,
                    ocr_pipeline_runs_table.c.status == "cancelling",
                )
                .values(diagnostics=diagnostics, updated_at=func.clock_timestamp())
            )
        return "recorded"

    async def _enqueue_cancellation_command(
        self,
        record: OcrPipelineRunRecord,
        attempt: Mapping[str, object],
        *,
        requested_at: datetime,
    ) -> None:
        run_id = record.id
        command = OcrRunCancellationRequestedV1(
            run_id=str(run_id),
            document_id=str(record.document_id),
            pipeline_id=str(record.pipeline_id),
            attempt_id=str(attempt["attempt_id"]),
            fencing_token=int(cast(int, attempt["fencing_token"])),
            next_event_sequence=max(
                2,
                int(cast(int, attempt.get("last_event_sequence") or 0)) + 1,
            ),
            correlation_id=str(run_id),
            requested_at=(
                requested_at.astimezone(UTC)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            ),
        )
        await self._session.execute(
            postgresql_insert(ocr_pipeline_run_outbox_table)
            .values(
                id=uuid4(),
                run_id=run_id,
                topic=OCR_DOCUMENT_PROCESSING_TOPIC,
                event_type=OCR_RUN_CANCELLATION_REQUESTED_EVENT_TYPE,
                payload=command.model_dump(mode="json"),
                created_at=requested_at,
                available_at=requested_at,
                dedupe_key=(
                    f"ocr-cancel:{run_id}:{attempt['attempt_id']}:{attempt['fencing_token']}"
                ),
            )
            .on_conflict_do_nothing(
                index_elements=[ocr_pipeline_run_outbox_table.c.dedupe_key],
                index_where=(
                    ocr_pipeline_run_outbox_table.c.published_at.is_(None)
                    & ocr_pipeline_run_outbox_table.c.dedupe_key.is_not(None)
                ),
            )
        )

    async def reconcile_cancellations(self) -> int:
        """Terminalize cancellations not confirmed by LLM Magic before their deadline."""

        rows = (
            (
                await self._session.execute(
                    select(
                        ocr_pipeline_run_attempts_table.c.run_id,
                        ocr_pipeline_run_attempts_table.c.attempt_id,
                        ocr_pipeline_run_attempts_table.c.fencing_token,
                    )
                    .join(
                        ocr_pipeline_runs_table,
                        ocr_pipeline_runs_table.c.id == ocr_pipeline_run_attempts_table.c.run_id,
                    )
                    .where(
                        ocr_pipeline_runs_table.c.status == "cancelling",
                        ocr_pipeline_run_attempts_table.c.status == "running",
                        ocr_pipeline_run_attempts_table.c.cancellation_deadline_at
                        <= func.clock_timestamp(),
                    )
                )
            )
            .mappings()
            .all()
        )
        count = 0
        for row in rows:
            outcome = await self.complete_cancellation(
                cast(UUID, row["run_id"]),
                cast(UUID, row["attempt_id"]),
                fencing_token=int(row["fencing_token"]),
                error_code="OCR_PIPELINE_RUN_CANCELLATION_UNCONFIRMED",
            )
            if outcome == "cancelled":
                count += 1
        return count

    async def _lock_capacity(self) -> None:
        await self._session.execute(
            select(ocr_pipeline_run_capacity_lock_table.c.id)
            .where(ocr_pipeline_run_capacity_lock_table.c.id == 1)
            .with_for_update()
        )

    async def _current_attempt(
        self, run_id: UUID, attempt_id: UUID, fencing_token: int
    ) -> dict[str, object] | None:
        row = (
            (
                await self._session.execute(
                    select(ocr_pipeline_run_attempts_table)
                    .where(
                        ocr_pipeline_run_attempts_table.c.run_id == run_id,
                        ocr_pipeline_run_attempts_table.c.attempt_id == attempt_id,
                        ocr_pipeline_run_attempts_table.c.fencing_token == fencing_token,
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    async def _finish_attempt(
        self,
        attempt: Mapping[str, object],
        *,
        status: str,
        error_code: str,
        completed_at: datetime,
    ) -> None:
        attempt_id = cast(UUID, attempt["attempt_id"])
        await self._session.execute(
            update(ocr_pipeline_run_attempts_table)
            .where(ocr_pipeline_run_attempts_table.c.attempt_id == attempt_id)
            .values(status=status, completed_at=completed_at, error_code=error_code)
        )

    async def _enqueue_delayed_request(
        self,
        record: OcrPipelineRunRecord,
        *,
        available_at: datetime,
    ) -> bool:
        event = OcrRunRequestedV1(
            run_id=str(record.id),
            document_id=str(record.document_id),
            correlation_id=str(record.id),
            requested_at=available_at.astimezone(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        )
        statement = postgresql_insert(ocr_pipeline_run_outbox_table).values(
            id=uuid4(),
            run_id=record.id,
            topic=OCR_DOCUMENT_PROCESSING_TOPIC,
            event_type=OCR_RUN_REQUESTED_EVENT_TYPE,
            payload=event.model_dump(mode="json"),
            created_at=datetime.now(UTC),
            available_at=available_at,
            dedupe_key=f"ocr-dispatch:{record.id}",
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing(
                index_elements=[ocr_pipeline_run_outbox_table.c.dedupe_key],
                index_where=(
                    ocr_pipeline_run_outbox_table.c.published_at.is_(None)
                    & ocr_pipeline_run_outbox_table.c.dedupe_key.is_not(None)
                ),
            ).returning(ocr_pipeline_run_outbox_table.c.id)
        )
        inserted = result.scalar_one_or_none() is not None
        if inserted:
            record_ocr_admission_deferral()
        return inserted

    def _dispatchable_result(
        self,
        record: OcrPipelineRunRecord,
        attempt: dict[str, object],
    ) -> OcrEventDispatchResult:
        attempt_id = cast(UUID, attempt["attempt_id"])
        attempt_number = int(cast(int, attempt["attempt_number"]))
        fencing_token = int(cast(int, attempt["fencing_token"]))
        return OcrEventDispatchResult(
            disposition="dispatchable",
            attempt_id=attempt_id,
            attempt_number=attempt_number,
            fencing_token=fencing_token,
            execution_deadline_at=cast(datetime, attempt["execution_deadline_at"]),
            run_request=_event_run_request(
                record,
                attempt_id=attempt_id,
                attempt_number=attempt_number,
                fencing_token=fencing_token,
            ),
        )

    async def _invalidate_pending_run_requests(
        self, run_id: UUID, *, published_at: datetime
    ) -> None:
        await self._session.execute(
            update(ocr_pipeline_run_outbox_table)
            .where(
                ocr_pipeline_run_outbox_table.c.run_id == run_id,
                ocr_pipeline_run_outbox_table.c.event_type == OCR_RUN_REQUESTED_EVENT_TYPE,
                ocr_pipeline_run_outbox_table.c.published_at.is_(None),
            )
            .values(published_at=published_at)
        )

    async def _terminalize_cancelled_run(
        self,
        run_id: UUID,
        *,
        requested_at: datetime,
        actor_id: str,
        actor_login: str | None,
    ) -> None:
        await self._session.execute(
            update(ocr_pipeline_runs_table)
            .where(
                ocr_pipeline_runs_table.c.id == run_id,
                ocr_pipeline_runs_table.c.status.in_(("pending", "running")),
            )
            .values(
                status="cancelled",
                started_at=func.coalesce(ocr_pipeline_runs_table.c.started_at, requested_at),
                completed_at=requested_at,
                cancellation_requested_at=requested_at,
                cancellation_requested_by_actor_id=actor_id,
                cancellation_requested_by_actor_login=actor_login,
                updated_at=requested_at,
            )
        )

    async def _latest_attempt(
        self,
        run_id: UUID,
        *,
        lock: bool = False,
    ) -> dict[str, object] | None:
        statement = (
            select(ocr_pipeline_run_attempts_table)
            .where(ocr_pipeline_run_attempts_table.c.run_id == run_id)
            .order_by(ocr_pipeline_run_attempts_table.c.attempt_number.desc())
            .limit(1)
        )
        if lock:
            statement = statement.with_for_update()
        row = (await self._session.execute(statement)).mappings().one_or_none()
        return dict(row) if row is not None else None

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


def _event_run_request(
    record: OcrPipelineRunRecord,
    *,
    attempt_id: UUID,
    attempt_number: int,
    fencing_token: int,
) -> dict[str, object]:
    """Return the opaque LLM Magic pipeline-run request for one fenced attempt."""

    payload: dict[str, object] = {
        "document_reference": record.document_reference,
        "run_id": str(record.id),
        "metadata": {
            "pipeline_version": record.pipeline_version,
        },
        "compiled_definition": dict(record.compiled_snapshot),
        "trace_context": {
            "document_id": str(record.document_id),
            "attempt_id": str(attempt_id),
            "attempt_number": attempt_number,
            "fencing_token": fencing_token,
            "acquisition_reason": "new" if attempt_number == 1 else "retry",
            "actor_type": record.started_by_actor_type.value,
            "actor_internal_id": record.started_by_actor_id,
            "actor_login_missing": (
                record.started_by_actor_type == OcrPipelineRunActorType.HUMAN
                and record.started_by_actor_login is None
            ),
            "document_source": record.document_source,
            "document_connector": record.document_connector,
            "connector_instance_id": record.connector_instance_id,
            "connector_display_name": record.connector_display_name,
            "connector_correlation_id": record.connector_correlation_id,
            "correlation_id": None,
        },
    }
    if record.started_by_actor_type == OcrPipelineRunActorType.HUMAN:
        if record.started_by_actor_login is not None:
            payload["user_id"] = record.started_by_actor_login
    elif record.started_by_actor_type == OcrPipelineRunActorType.CONNECTOR:
        if record.started_by_actor_id is not None:
            payload["user_id"] = record.started_by_actor_id
    return payload


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
