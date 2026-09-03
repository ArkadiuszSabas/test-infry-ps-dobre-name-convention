"""SQL persistence adapter for administrative OCR run monitoring."""

from collections.abc import Mapping, Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import String, and_, func, or_, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from docmind_api.application.ocr_pipeline_runs.admin_read_model import (
    AdminOcrRunAttempt,
    AdminOcrRunDetail,
    AdminOcrRunFilters,
    AdminOcrRunPage,
    AdminOcrRunSummary,
)
from docmind_api.domain.ocr_pipeline_runs.models import OcrPipelineRunStatus
from docmind_api.infrastructure.persistence.document_types.tables import document_types_table
from docmind_api.infrastructure.persistence.documents.tables import documents_table
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.mappers import (
    diagnostic_from_json,
    error_from_json,
    metric_object,
    optional_string,
    step_from_json,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.tables import (
    ocr_pipeline_run_attempts_table,
    ocr_pipeline_runs_table,
)
from docmind_api.infrastructure.persistence.ocr_pipelines.tables import (
    ocr_pipeline_definitions_table,
)

_ACTIVE_STATUSES = ("pending", "running", "cancelling")
_TERMINAL_STATUSES = ("succeeded", "partial_failed", "failed", "cancelled")


class SqlAlchemyAdminOcrRunReadRepository:
    """Read cross-document OCR run state without loading result payloads."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_runs(self, filters: AdminOcrRunFilters) -> AdminOcrRunPage:
        rows = (
            (
                await self._session.execute(
                    build_admin_ocr_run_list_statement(filters).limit(filters.limit + 1)
                )
            )
            .mappings()
            .all()
        )
        has_more = len(rows) > filters.limit
        return AdminOcrRunPage(
            runs=tuple(_summary_from_row(row) for row in rows[: filters.limit]),
            limit=filters.limit,
            offset=filters.offset,
            has_more=has_more,
        )

    async def get_run(self, run_id: UUID) -> AdminOcrRunDetail | None:
        row = (
            (
                await self._session.execute(
                    _base_statement(include_detail=True).where(
                        ocr_pipeline_runs_table.c.id == run_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        attempt_rows = (
            (
                await self._session.execute(
                    select(ocr_pipeline_run_attempts_table)
                    .where(ocr_pipeline_run_attempts_table.c.run_id == run_id)
                    .order_by(ocr_pipeline_run_attempts_table.c.attempt_number.asc())
                )
            )
            .mappings()
            .all()
        )
        return AdminOcrRunDetail(
            run=_summary_from_row(row),
            steps=tuple(
                step_from_json(cast(Mapping[Any, Any], item))
                for item in _json_sequence(row["steps"])
            ),
            metrics=metric_object(cast(Mapping[str, Any], row["metrics"])),
            diagnostics=tuple(
                diagnostic_from_json(cast(Mapping[Any, Any], item))
                for item in _json_sequence(row["diagnostics"])
            ),
            error=error_from_json(cast(Mapping[Any, Any] | None, row["error"])),
            attempts=tuple(_attempt_from_row(item) for item in attempt_rows),
            cancellation_requested_at=row["cancellation_requested_at"],
            cancellation_requested_by_actor_id=optional_string(
                row["cancellation_requested_by_actor_id"]
            ),
            cancellation_requested_by_actor_login=optional_string(
                row["cancellation_requested_by_actor_login"]
            ),
        )


def build_admin_ocr_run_list_statement(
    filters: AdminOcrRunFilters,
) -> Select[tuple[Any, ...]]:
    """Build the bounded, composable statement used by the admin list."""

    statement = _base_statement(include_detail=False)
    status_values = tuple(status.value for status in filters.statuses)
    statement = statement.where(
        ocr_pipeline_runs_table.c.status.in_(
            status_values or (_ACTIVE_STATUSES if filters.view == "active" else _TERMINAL_STATUSES)
        )
    )
    if filters.pipeline_id is not None:
        statement = statement.where(ocr_pipeline_runs_table.c.pipeline_id == filters.pipeline_id)
    if filters.document_type_id is not None:
        statement = statement.where(documents_table.c.document_type_id == filters.document_type_id)
    if filters.source is not None:
        statement = statement.where(ocr_pipeline_runs_table.c.document_source == filters.source)
    if filters.connector is not None:
        statement = statement.where(
            or_(
                ocr_pipeline_runs_table.c.document_connector == filters.connector,
                ocr_pipeline_runs_table.c.connector_instance_id == filters.connector,
            )
        )
    if filters.created_from is not None:
        statement = statement.where(ocr_pipeline_runs_table.c.created_at >= filters.created_from)
    if filters.created_to is not None:
        statement = statement.where(ocr_pipeline_runs_table.c.created_at <= filters.created_to)
    if filters.updated_before is not None:
        statement = statement.where(ocr_pipeline_runs_table.c.updated_at <= filters.updated_before)
    if filters.search is not None:
        pattern = f"%{filters.search}%"
        statement = statement.where(
            or_(
                documents_table.c.original_filename.ilike(pattern),
                sql_cast(documents_table.c.id, String).ilike(pattern),
                sql_cast(ocr_pipeline_runs_table.c.id, String).ilike(pattern),
                ocr_pipeline_runs_table.c.connector_correlation_id.ilike(pattern),
            )
        )
    candidate_ordering = (
        (ocr_pipeline_runs_table.c.updated_at.asc(), ocr_pipeline_runs_table.c.id.asc())
        if filters.view == "active"
        else (ocr_pipeline_runs_table.c.completed_at.desc(), ocr_pipeline_runs_table.c.id.desc())
    )
    ranked_runs = statement.add_columns(
        func.row_number()
        .over(
            partition_by=ocr_pipeline_runs_table.c.document_id,
            order_by=candidate_ordering,
        )
        .label("_document_rank")
    ).subquery()
    result_columns = [column for column in ranked_runs.c if column.key != "_document_rank"]
    result_ordering = (
        (ranked_runs.c.updated_at.asc(), ranked_runs.c.id.asc())
        if filters.view == "active"
        else (ranked_runs.c.completed_at.desc(), ranked_runs.c.id.desc())
    )
    return (
        select(*result_columns)
        .where(ranked_runs.c._document_rank == 1)
        .order_by(*result_ordering)
        .offset(filters.offset)
    )


def _base_statement(*, include_detail: bool) -> Select[tuple[Any, ...]]:
    latest_attempt_number = (
        select(func.max(ocr_pipeline_run_attempts_table.c.attempt_number))
        .where(ocr_pipeline_run_attempts_table.c.run_id == ocr_pipeline_runs_table.c.id)
        .correlate(ocr_pipeline_runs_table)
        .scalar_subquery()
    )
    columns = [
        ocr_pipeline_runs_table.c.id,
        ocr_pipeline_runs_table.c.document_id,
        documents_table.c.original_filename.label("document_name"),
        documents_table.c.document_type_id,
        document_types_table.c.name.label("document_type_name"),
        ocr_pipeline_runs_table.c.pipeline_id,
        ocr_pipeline_definitions_table.c.display_name.label("pipeline_name"),
        ocr_pipeline_runs_table.c.pipeline_version,
        ocr_pipeline_runs_table.c.status,
        ocr_pipeline_runs_table.c.steps,
        ocr_pipeline_runs_table.c.started_by_actor_id,
        ocr_pipeline_runs_table.c.started_by_actor_type,
        ocr_pipeline_runs_table.c.started_by_actor_login,
        ocr_pipeline_runs_table.c.document_source,
        ocr_pipeline_runs_table.c.document_connector,
        ocr_pipeline_runs_table.c.connector_instance_id,
        ocr_pipeline_runs_table.c.connector_display_name,
        ocr_pipeline_runs_table.c.connector_correlation_id,
        ocr_pipeline_runs_table.c.created_at,
        ocr_pipeline_runs_table.c.started_at,
        ocr_pipeline_runs_table.c.updated_at,
        ocr_pipeline_runs_table.c.completed_at,
        *[
            column.label(f"latest_attempt_{column.name}")
            for column in ocr_pipeline_run_attempts_table.c
            if column.name not in {"run_id", "owner_token", "fencing_token"}
        ],
    ]
    if include_detail:
        columns.extend(
            [
                ocr_pipeline_runs_table.c.metrics,
                ocr_pipeline_runs_table.c.diagnostics,
                ocr_pipeline_runs_table.c.error,
                ocr_pipeline_runs_table.c.cancellation_requested_at,
                ocr_pipeline_runs_table.c.cancellation_requested_by_actor_id,
                ocr_pipeline_runs_table.c.cancellation_requested_by_actor_login,
            ]
        )
    return select(*columns).select_from(
        ocr_pipeline_runs_table.join(
            documents_table,
            documents_table.c.id == ocr_pipeline_runs_table.c.document_id,
        )
        .join(
            document_types_table,
            document_types_table.c.id == documents_table.c.document_type_id,
        )
        .join(
            ocr_pipeline_definitions_table,
            ocr_pipeline_definitions_table.c.id == ocr_pipeline_runs_table.c.pipeline_id,
        )
        .outerjoin(
            ocr_pipeline_run_attempts_table,
            and_(
                ocr_pipeline_run_attempts_table.c.run_id == ocr_pipeline_runs_table.c.id,
                ocr_pipeline_run_attempts_table.c.attempt_number == latest_attempt_number,
            ),
        )
    )


def _summary_from_row(row: Mapping[Any, Any]) -> AdminOcrRunSummary:
    steps = [step_from_json(cast(Mapping[Any, Any], item)) for item in _json_sequence(row["steps"])]
    current = next((step for step in steps if step.status.value in {"running", "pending"}), None)
    completed = sum(step.status.value in {"succeeded", "failed", "skipped"} for step in steps)
    return AdminOcrRunSummary(
        id=cast(UUID, row["id"]),
        document_id=cast(UUID, row["document_id"]),
        document_name=str(row["document_name"]),
        document_type_id=cast(UUID, row["document_type_id"]),
        document_type_name=str(row["document_type_name"]),
        pipeline_id=cast(UUID, row["pipeline_id"]),
        pipeline_name=optional_string(row["pipeline_name"]),
        pipeline_version=int(row["pipeline_version"]),
        status=OcrPipelineRunStatus(str(row["status"])),
        current_step_name=current.display_name if current else None,
        current_step_status=current.status.value if current else None,
        completed_step_count=completed,
        total_step_count=len(steps),
        started_by_actor_id=optional_string(row["started_by_actor_id"]),
        started_by_actor_type=str(row["started_by_actor_type"]),
        started_by_actor_login=optional_string(row["started_by_actor_login"]),
        document_source=optional_string(row["document_source"]),
        document_connector=optional_string(row["document_connector"]),
        connector_instance_id=optional_string(row["connector_instance_id"]),
        connector_display_name=optional_string(row["connector_display_name"]),
        connector_correlation_id=optional_string(row["connector_correlation_id"]),
        created_at=row["created_at"],
        started_at=row["started_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
        latest_attempt=(
            _attempt_from_row(row, prefix="latest_attempt_")
            if row["latest_attempt_attempt_id"] is not None
            else None
        ),
    )


def _attempt_from_row(row: Mapping[Any, Any], *, prefix: str = "") -> AdminOcrRunAttempt:
    return AdminOcrRunAttempt(
        attempt_id=cast(UUID, row[f"{prefix}attempt_id"]),
        attempt_number=int(row[f"{prefix}attempt_number"]),
        status=str(row[f"{prefix}status"]),
        started_at=row[f"{prefix}started_at"],
        invocation_started_at=row[f"{prefix}invocation_started_at"],
        last_renewed_at=row[f"{prefix}last_renewed_at"],
        lease_expires_at=row[f"{prefix}lease_expires_at"],
        completed_at=row[f"{prefix}completed_at"],
        error_code=optional_string(row[f"{prefix}error_code"]),
        execution_deadline_at=row[f"{prefix}execution_deadline_at"],
        cancellation_deadline_at=row[f"{prefix}cancellation_deadline_at"],
        last_event_sequence=int(row[f"{prefix}last_event_sequence"]),
    )


def _json_sequence(value: object) -> Sequence[object]:
    if isinstance(value, list | tuple):
        return cast(Sequence[object], value)
    return ()
