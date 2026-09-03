"""Database-aggregated operational dashboard reader."""

from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.dashboard.models import (
    DashboardActivityDay,
    DashboardArchiveSummary,
    DashboardDocumentItem,
    DashboardOcrTiming,
    DashboardOperationalStatus,
    DashboardOverview,
)
from docmind_api.domain.documents.models import DocumentStatus
from docmind_api.domain.ocr_pipeline_runs.statuses import (
    ACTIVE_OCR_PIPELINE_RUN_STATUSES,
    OcrPipelineRunStatus,
    OcrPipelineRunStepStatus,
)

_ACTIVITY_SQL = text(
    """
    with days as (
        select generate_series(
            cast(:window_start_date as date),
            cast(:window_end_date as date),
            interval '1 day'
        )::date as activity_date
    ),
    visible_documents as (
        select documents.*
        from documents
        where not exists (
            select 1
            from document_deletion_operations
            where document_deletion_operations.document_id = documents.id
              and document_deletion_operations.stage <> 'completed'
        )
    ),
    accepted as (
        select created_at::date as activity_date, count(*)::integer as event_count
        from visible_documents
        where created_at >= :window_start and created_at <= :generated_at
        group by created_at::date
    ),
    successful_ocr as (
        select runs.completed_at::date as activity_date,
               count(distinct runs.id)::integer as event_count
        from ocr_pipeline_runs as runs
        join lateral (
            select item.step
            from jsonb_array_elements(runs.steps) with ordinality as item(step, ordinal)
            where item.step ->> 'step_type' = :ocr_step_type
              and item.step ->> 'status' = :succeeded_step_status
            order by item.ordinal
            limit 1
        ) as successful_step on true
        where runs.completed_at >= :window_start
          and runs.completed_at <= :generated_at
          and not exists (
              select 1
              from document_deletion_operations
              where document_deletion_operations.document_id = runs.document_id
                and document_deletion_operations.stage <> 'completed'
          )
        group by runs.completed_at::date
    ),
    archived as (
        select updated_at::date as activity_date, count(*)::integer as event_count
        from visible_documents
        where status = :approved_document_status
          and updated_at >= :window_start
          and updated_at <= :generated_at
        group by updated_at::date
    )
    select days.activity_date,
           coalesce(accepted.event_count, 0)::integer as accepted,
           coalesce(successful_ocr.event_count, 0)::integer as successful_ocr,
           coalesce(archived.event_count, 0)::integer as archived
    from days
    left join accepted using (activity_date)
    left join successful_ocr using (activity_date)
    left join archived using (activity_date)
    order by days.activity_date
    """
)

_OCR_TIMING_SQL = text(
    """
    with samples as (
        select runs.id,
               (successful_step.step ->> 'duration_seconds')::double precision
                   as duration_seconds,
               case
                   when jsonb_typeof(
                       successful_step.step -> 'metrics' -> 'page_count'
                   ) = 'number'
                   and (
                       successful_step.step -> 'metrics' ->> 'page_count'
                   )::double precision > 0
                   then (
                       successful_step.step -> 'metrics' ->> 'page_count'
                   )::double precision
                   else null
               end as page_count
        from ocr_pipeline_runs as runs
        join lateral (
            select item.step
            from jsonb_array_elements(runs.steps) with ordinality as item(step, ordinal)
            where item.step ->> 'step_type' = :ocr_step_type
              and item.step ->> 'status' = :succeeded_step_status
              and jsonb_typeof(item.step -> 'duration_seconds') = 'number'
              and (item.step ->> 'duration_seconds')::double precision >= 0
            order by item.ordinal
            limit 1
        ) as successful_step on true
        where runs.completed_at >= :window_start
          and runs.completed_at <= :generated_at
          and not exists (
              select 1
              from document_deletion_operations
              where document_deletion_operations.document_id = runs.document_id
                and document_deletion_operations.stage <> 'completed'
          )
    )
    select count(*)::integer as successful_sample_count,
           min(duration_seconds) as min_seconds,
           avg(duration_seconds) as average_seconds,
           max(duration_seconds) as max_seconds,
           (
               sum(duration_seconds) filter (where page_count is not null)
               / nullif(sum(page_count) filter (where page_count is not null), 0)
           ) as weighted_average_seconds_per_page
    from samples
    """
)

_SUMMARY_SQL = text(
    """
    with visible_documents as (
        select documents.*
        from documents
        where not exists (
            select 1
            from document_deletion_operations
            where document_deletion_operations.document_id = documents.id
              and document_deletion_operations.stage <> 'completed'
        )
    ),
    latest_runs as (
        select distinct on (document_id)
               document_id,
               status,
               error,
               coalesce(completed_at, updated_at) as event_at
        from ocr_pipeline_runs
        order by document_id, created_at desc, id desc
    )
    select
        (
            select count(*) from visible_documents
            where status in (:waiting_document_status, :in_review_document_status)
        )::integer as to_review,
        (
            select count(distinct runs.document_id)
            from ocr_pipeline_runs as runs
            join visible_documents on visible_documents.id = runs.document_id
            where runs.status in (
                :pending_run_status, :running_run_status, :cancelling_run_status
            )
        )::integer as processing,
        (
            select count(*)
            from latest_runs
            join visible_documents as documents on documents.id = latest_runs.document_id
            where latest_runs.status in (:failed_run_status, :partial_failed_run_status)
              and documents.status <> :approved_document_status
        )::integer as requires_attention,
        (
            select count(*) from visible_documents
            where status = :approved_document_status
        )::integer as archive_total,
        (
            select count(*) from visible_documents
            where status = :approved_document_status
              and updated_at >= :window_start
              and updated_at <= :generated_at
        )::integer as archive_added_in_window
    """
)

_TO_REVIEW_SQL = text(
    """
    with visible_documents as (
        select documents.*
        from documents
        where not exists (
            select 1
            from document_deletion_operations
            where document_deletion_operations.document_id = documents.id
              and document_deletion_operations.stage <> 'completed'
        )
    )
    select documents.id as document_id,
           documents.original_filename as filename,
           document_types.name as document_type,
           documents.status,
           null::text as problem_type,
           documents.updated_at as event_at
    from visible_documents as documents
    left join document_types on document_types.id = documents.document_type_id
    where documents.status in (:waiting_document_status, :in_review_document_status)
    order by documents.created_at desc, documents.id desc
    limit 3
    """
)

_REQUIRES_ATTENTION_SQL = text(
    """
    with visible_documents as (
        select documents.*
        from documents
        where not exists (
            select 1
            from document_deletion_operations
            where document_deletion_operations.document_id = documents.id
              and document_deletion_operations.stage <> 'completed'
        )
    ),
    latest_runs as (
        select distinct on (document_id)
               document_id,
               status,
               error,
               coalesce(completed_at, updated_at) as event_at
        from ocr_pipeline_runs
        order by document_id, created_at desc, id desc
    )
    select documents.id as document_id,
           documents.original_filename as filename,
           document_types.name as document_type,
           latest_runs.status,
           coalesce(latest_runs.error ->> 'code', latest_runs.status) as problem_type,
           latest_runs.event_at
    from latest_runs
    join visible_documents as documents on documents.id = latest_runs.document_id
    left join document_types on document_types.id = documents.document_type_id
    where latest_runs.status in (:failed_run_status, :partial_failed_run_status)
      and documents.status <> :approved_document_status
    order by latest_runs.event_at desc, documents.id desc
    limit 3
    """
)


class SqlAlchemyDashboardOverviewReader:
    """Read dashboard aggregates from persisted API-owned product state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_overview(
        self,
        *,
        window_days: int,
        generated_at: datetime,
    ) -> DashboardOverview:
        """Return a complete snapshot using database-side aggregation."""

        normalized_generated_at = generated_at.astimezone(UTC)
        window_start_date = normalized_generated_at.date() - timedelta(days=window_days - 1)
        window_start = datetime.combine(window_start_date, time.min, tzinfo=UTC)
        params = {
            "approved_document_status": DocumentStatus.APPROVED.value,
            "failed_run_status": OcrPipelineRunStatus.FAILED.value,
            "generated_at": normalized_generated_at,
            "in_review_document_status": DocumentStatus.IN_REVIEW.value,
            "ocr_step_type": "ocr_parsing",
            "partial_failed_run_status": OcrPipelineRunStatus.PARTIAL_FAILED.value,
            "cancelling_run_status": OcrPipelineRunStatus.CANCELLING.value,
            "pending_run_status": ACTIVE_OCR_PIPELINE_RUN_STATUSES[0].value,
            "running_run_status": ACTIVE_OCR_PIPELINE_RUN_STATUSES[1].value,
            "succeeded_step_status": OcrPipelineRunStepStatus.SUCCEEDED.value,
            "waiting_document_status": DocumentStatus.WAITING_FOR_REVIEW.value,
            "window_start": window_start,
            "window_start_date": window_start_date,
            "window_end_date": normalized_generated_at.date(),
        }

        activity_rows = (await self._session.execute(_ACTIVITY_SQL, params)).mappings().all()
        timing_row = (await self._session.execute(_OCR_TIMING_SQL, params)).mappings().one()
        summary_row = (await self._session.execute(_SUMMARY_SQL, params)).mappings().one()
        to_review_rows = (await self._session.execute(_TO_REVIEW_SQL, params)).mappings().all()
        attention_rows = (
            (await self._session.execute(_REQUIRES_ATTENTION_SQL, params)).mappings().all()
        )

        return DashboardOverview(
            generated_at=normalized_generated_at,
            window_days=window_days,
            operational_status=DashboardOperationalStatus(
                to_review=int(summary_row["to_review"]),
                processing=int(summary_row["processing"]),
                requires_attention=int(summary_row["requires_attention"]),
            ),
            activity=tuple(_activity_day(row) for row in activity_rows),
            ocr_timing=DashboardOcrTiming(
                successful_sample_count=int(timing_row["successful_sample_count"]),
                min_seconds=_optional_float(timing_row["min_seconds"]),
                average_seconds=_optional_float(timing_row["average_seconds"]),
                max_seconds=_optional_float(timing_row["max_seconds"]),
                weighted_average_seconds_per_page=_optional_float(
                    timing_row["weighted_average_seconds_per_page"],
                ),
            ),
            archive=DashboardArchiveSummary(
                total=int(summary_row["archive_total"]),
                added_in_window=int(summary_row["archive_added_in_window"]),
            ),
            to_review=tuple(_document_item(row) for row in to_review_rows),
            requires_attention=tuple(_document_item(row) for row in attention_rows),
        )


def _activity_day(row: Mapping[Any, Any]) -> DashboardActivityDay:
    return DashboardActivityDay(
        date=cast(date, row["activity_date"]),
        accepted=int(row["accepted"]),
        successful_ocr=int(row["successful_ocr"]),
        archived=int(row["archived"]),
    )


def _document_item(row: Mapping[Any, Any]) -> DashboardDocumentItem:
    return DashboardDocumentItem(
        document_id=cast(UUID, row["document_id"]),
        filename=str(row["filename"]),
        document_type=(str(row["document_type"]) if row["document_type"] is not None else None),
        status=str(row["status"]),
        problem_type=(str(row["problem_type"]) if row["problem_type"] is not None else None),
        event_at=cast(datetime, row["event_at"]),
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float | Decimal):
        return float(value)
    raise TypeError("Dashboard aggregate returned a non-numeric value.")
