"""Atomic PostgreSQL operations for OCR pipeline execution ownership."""

from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.domain.ocr_pipeline_runs.models import (
    OcrPipelineRunAcquireDisposition,
    OcrPipelineRunAcquireReason,
    OcrPipelineRunAcquireResult,
    OcrPipelineRunAttemptStatus,
    OcrPipelineRunDiagnostic,
    OcrPipelineRunDiagnosticSeverity,
    OcrPipelineRunError,
    OcrPipelineRunExecutionAttempt,
    OcrPipelineRunExecutionLease,
    OcrPipelineRunRecord,
    OcrPipelineRunStatus,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.execution_mapping import (
    attempt_from_row,
    exhausted_record,
    lease_from_row,
    lease_identity_predicates,
    mutable_run_values,
    reset_record_for_attempt,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.execution_policy import (
    acquire_reason,
    non_acquired_disposition,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.mappers import (
    record_from_row,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.tables import (
    ocr_pipeline_run_attempts_table,
    ocr_pipeline_runs_table,
)

_REUSABLE_RUN_STATUSES = frozenset(
    {OcrPipelineRunStatus.SUCCEEDED, OcrPipelineRunStatus.PARTIAL_FAILED}
)


async def fail_stale_executions(
    session: AsyncSession,
    *,
    stale_after_seconds: float,
) -> int:
    """Fail runs that exceed the configured manual-retry deadline.

    PostgreSQL row locks make concurrent watchdogs from separate API replicas safe.
    """

    observed_at = await _database_now(session)
    stale_before = observed_at - timedelta(seconds=stale_after_seconds)
    run_rows = (
        (
            await session.execute(
                select(ocr_pipeline_runs_table)
                .where(
                    ocr_pipeline_runs_table.c.status.in_(
                        (OcrPipelineRunStatus.PENDING.value, OcrPipelineRunStatus.RUNNING.value)
                    ),
                    func.coalesce(
                        ocr_pipeline_runs_table.c.started_at,
                        ocr_pipeline_runs_table.c.created_at,
                    )
                    <= stale_before,
                )
                .with_for_update(skip_locked=True)
            )
        )
        .mappings()
        .all()
    )
    failed_count = 0
    for run_row in run_rows:
        record = record_from_row(run_row)
        latest_row = await _latest_attempt_row(session, record.id)
        latest = attempt_from_row(latest_row) if latest_row is not None else None
        if not _can_fail_as_stale(record, latest):
            continue

        timeout_record = _stale_timeout_record(record, completed_at=observed_at)
        if latest is not None:
            await session.execute(
                update(ocr_pipeline_run_attempts_table)
                .where(
                    ocr_pipeline_run_attempts_table.c.attempt_id == latest.attempt_id,
                    ocr_pipeline_run_attempts_table.c.status.in_(
                        (
                            OcrPipelineRunAttemptStatus.RUNNING.value,
                            OcrPipelineRunAttemptStatus.INDETERMINATE.value,
                        )
                    ),
                )
                .values(
                    status=OcrPipelineRunAttemptStatus.FAILED.value,
                    completed_at=observed_at,
                    error_code="OCR_PIPELINE_RUN_EXECUTION_TIMEOUT",
                )
            )
        result = await session.execute(
            update(ocr_pipeline_runs_table)
            .where(
                ocr_pipeline_runs_table.c.id == record.id,
                ocr_pipeline_runs_table.c.status.in_(
                    (OcrPipelineRunStatus.PENDING.value, OcrPipelineRunStatus.RUNNING.value)
                ),
            )
            .values(**mutable_run_values(timeout_record))
            .returning(ocr_pipeline_runs_table.c.id)
        )
        if result.scalar_one_or_none() is not None:
            failed_count += 1
    return failed_count


def _can_fail_as_stale(
    record: OcrPipelineRunRecord,
    latest: OcrPipelineRunExecutionAttempt | None,
) -> bool:
    if record.status == OcrPipelineRunStatus.PENDING:
        return latest is None
    return latest is not None and latest.status in (
        OcrPipelineRunAttemptStatus.RUNNING,
        OcrPipelineRunAttemptStatus.INDETERMINATE,
    )


def _stale_timeout_record(
    record: OcrPipelineRunRecord,
    *,
    completed_at: datetime,
) -> OcrPipelineRunRecord:
    code = "OCR_PIPELINE_RUN_EXECUTION_TIMEOUT"
    return replace(
        record,
        status=OcrPipelineRunStatus.FAILED,
        diagnostics=(
            *record.diagnostics,
            OcrPipelineRunDiagnostic(
                severity=OcrPipelineRunDiagnosticSeverity.ERROR,
                code=code,
                message="OCR pipeline run exceeded the execution recovery deadline.",
            ),
        ),
        error=OcrPipelineRunError(
            code=code,
            message="OCR pipeline run timed out before completion.",
        ),
        started_at=record.started_at or completed_at,
        completed_at=completed_at,
        updated_at=completed_at,
    )


async def acquire_execution(
    session: AsyncSession,
    run_id: UUID,
    *,
    attempt_id: UUID,
    owner_token: UUID,
    acquired_at: datetime,
    lease_expires_at: datetime,
    max_attempts: int,
) -> OcrPipelineRunAcquireResult | None:
    """Atomically acquire, reject, reuse, retry, or take over one logical run."""

    lease_duration = lease_expires_at - acquired_at
    run_row = (
        (
            await session.execute(
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

    acquired_at = await _database_now(session)
    lease_expires_at = acquired_at + lease_duration
    record = record_from_row(run_row)
    latest_row = await _latest_attempt_row(session, run_id)
    latest = attempt_from_row(latest_row) if latest_row is not None else None

    if record.status in _REUSABLE_RUN_STATUSES:
        await _close_legacy_running_attempt(session, latest, record, acquired_at)
        return OcrPipelineRunAcquireResult(
            disposition=OcrPipelineRunAcquireDisposition.RESULT_REUSED,
            record=record,
        )
    if (
        record.status == OcrPipelineRunStatus.FAILED
        and latest is not None
        and latest.status == OcrPipelineRunAttemptStatus.RUNNING
    ):
        await _close_legacy_running_attempt(session, latest, record, acquired_at)
        latest = replace(
            latest,
            status=OcrPipelineRunAttemptStatus.FAILED,
            completed_at=record.completed_at or acquired_at,
            error_code=record.error.code if record.error is not None else None,
        )

    reason = acquire_reason(record, latest, acquired_at)
    if reason is None:
        disposition = non_acquired_disposition(record, latest, acquired_at, max_attempts)
        return OcrPipelineRunAcquireResult(disposition=disposition, record=record)

    prior_attempt_number = latest.attempt_number if latest is not None else 0
    if prior_attempt_number >= max_attempts:
        if reason == OcrPipelineRunAcquireReason.EXPIRED_LEASE_TAKEOVER and latest is not None:
            await _mark_attempt_lost(session, latest, acquired_at)
            record = exhausted_record(record, completed_at=acquired_at)
            await session.execute(
                update(ocr_pipeline_runs_table)
                .where(ocr_pipeline_runs_table.c.id == run_id)
                .values(**mutable_run_values(record))
            )
        return OcrPipelineRunAcquireResult(
            disposition=OcrPipelineRunAcquireDisposition.RETRY_EXHAUSTED,
            record=record,
        )

    if reason == OcrPipelineRunAcquireReason.EXPIRED_LEASE_TAKEOVER:
        if latest is None:
            return OcrPipelineRunAcquireResult(
                disposition=OcrPipelineRunAcquireDisposition.AMBIGUOUS,
                record=record,
            )
        await _mark_attempt_lost(session, latest, acquired_at)

    attempt_number = prior_attempt_number + 1
    lease = OcrPipelineRunExecutionLease(
        run_id=run_id,
        attempt_id=attempt_id,
        owner_token=owner_token,
        attempt_number=attempt_number,
        fencing_token=attempt_number,
        acquired_at=acquired_at,
        last_renewed_at=acquired_at,
        lease_expires_at=lease_expires_at,
    )
    await session.execute(
        insert(ocr_pipeline_run_attempts_table).values(
            attempt_id=lease.attempt_id,
            run_id=lease.run_id,
            owner_token=lease.owner_token,
            attempt_number=lease.attempt_number,
            fencing_token=lease.fencing_token,
            status=OcrPipelineRunAttemptStatus.RUNNING.value,
            started_at=lease.acquired_at,
            invocation_started_at=None,
            last_renewed_at=lease.last_renewed_at,
            lease_expires_at=lease.lease_expires_at,
            completed_at=None,
            error_code=None,
        )
    )
    reset_record = reset_record_for_attempt(record, lease, reason)
    await session.execute(
        update(ocr_pipeline_runs_table)
        .where(ocr_pipeline_runs_table.c.id == run_id)
        .values(**mutable_run_values(reset_record))
    )
    return OcrPipelineRunAcquireResult(
        disposition=OcrPipelineRunAcquireDisposition.ACQUIRED,
        record=reset_record,
        lease=lease,
        reason=reason,
    )


async def renew_execution(
    session: AsyncSession,
    lease: OcrPipelineRunExecutionLease,
    *,
    renewed_at: datetime,
    lease_expires_at: datetime,
) -> OcrPipelineRunExecutionLease | None:
    """Renew only the still-current, unexpired owner lease."""

    lease_duration = lease_expires_at - renewed_at
    current = (
        (
            await session.execute(
                select(ocr_pipeline_run_attempts_table)
                .where(
                    *lease_identity_predicates(lease),
                    ocr_pipeline_run_attempts_table.c.status
                    == OcrPipelineRunAttemptStatus.RUNNING.value,
                )
                .with_for_update()
            )
        )
        .mappings()
        .one_or_none()
    )
    if current is None:
        return None
    renewed_at = await _database_now(session)
    if cast(datetime, current["lease_expires_at"]) <= renewed_at:
        return None
    lease_expires_at = renewed_at + lease_duration
    statement = (
        update(ocr_pipeline_run_attempts_table)
        .where(
            *lease_identity_predicates(lease),
            ocr_pipeline_run_attempts_table.c.status == OcrPipelineRunAttemptStatus.RUNNING.value,
        )
        .values(last_renewed_at=renewed_at, lease_expires_at=lease_expires_at)
        .returning(ocr_pipeline_run_attempts_table)
    )
    row = (await session.execute(statement)).mappings().one_or_none()
    if row is None:
        return None
    return lease_from_row(dict(row))


async def mark_execution_invocation_started(
    session: AsyncSession,
    lease: OcrPipelineRunExecutionLease,
) -> bool:
    """Persist the point after which an expired attempt must not be taken over."""

    result = await session.execute(
        update(ocr_pipeline_run_attempts_table)
        .where(
            *lease_identity_predicates(lease),
            ocr_pipeline_run_attempts_table.c.status == OcrPipelineRunAttemptStatus.RUNNING.value,
            ocr_pipeline_run_attempts_table.c.lease_expires_at > func.clock_timestamp(),
            ocr_pipeline_run_attempts_table.c.invocation_started_at.is_(None),
        )
        .values(invocation_started_at=func.clock_timestamp())
        .returning(ocr_pipeline_run_attempts_table.c.attempt_id)
    )
    return result.scalar_one_or_none() is not None


async def save_execution_result(
    session: AsyncSession,
    lease: OcrPipelineRunExecutionLease,
    record: OcrPipelineRunRecord,
    *,
    completed_at: datetime,
) -> bool:
    """Persist a terminal result only for the current unexpired fenced owner."""

    if record.id != lease.run_id or not record.is_terminal:
        return False
    run_locked = (
        await session.execute(
            select(ocr_pipeline_runs_table.c.id)
            .where(ocr_pipeline_runs_table.c.id == lease.run_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if run_locked is None:
        return False

    completed_at = await _database_now(session)
    status = OcrPipelineRunAttemptStatus(record.status.value)
    attempt_result = await session.execute(
        update(ocr_pipeline_run_attempts_table)
        .where(
            *lease_identity_predicates(lease),
            ocr_pipeline_run_attempts_table.c.status == OcrPipelineRunAttemptStatus.RUNNING.value,
            ocr_pipeline_run_attempts_table.c.lease_expires_at > completed_at,
        )
        .values(
            status=status.value,
            completed_at=completed_at,
            error_code=record.error.code if record.error is not None else None,
        )
        .returning(ocr_pipeline_run_attempts_table.c.attempt_id)
    )
    if attempt_result.scalar_one_or_none() is None:
        return False

    persisted = replace(record, completed_at=completed_at, updated_at=completed_at)
    run_result = await session.execute(
        update(ocr_pipeline_runs_table)
        .where(ocr_pipeline_runs_table.c.id == lease.run_id)
        .values(**mutable_run_values(persisted))
        .returning(ocr_pipeline_runs_table.c.id)
    )
    return run_result.scalar_one_or_none() is not None


async def record_execution_error(
    session: AsyncSession,
    lease: OcrPipelineRunExecutionLease,
    *,
    error_code: str,
    updated_at: datetime,
) -> bool:
    """End ownership as indeterminate without allowing automatic takeover."""

    result = await session.execute(
        update(ocr_pipeline_run_attempts_table)
        .where(
            *lease_identity_predicates(lease),
            ocr_pipeline_run_attempts_table.c.status == OcrPipelineRunAttemptStatus.RUNNING.value,
            ocr_pipeline_run_attempts_table.c.lease_expires_at > func.clock_timestamp(),
        )
        .values(
            status=OcrPipelineRunAttemptStatus.INDETERMINATE.value,
            completed_at=func.clock_timestamp(),
            error_code=error_code,
        )
        .returning(ocr_pipeline_run_attempts_table.c.attempt_id)
    )
    return result.scalar_one_or_none() is not None


async def _database_now(session: AsyncSession) -> datetime:
    return cast(datetime, (await session.execute(select(func.clock_timestamp()))).scalar_one())


async def get_execution_attempt(
    session: AsyncSession,
    attempt_id: UUID,
) -> OcrPipelineRunExecutionAttempt | None:
    row = (
        (
            await session.execute(
                select(ocr_pipeline_run_attempts_table).where(
                    ocr_pipeline_run_attempts_table.c.attempt_id == attempt_id
                )
            )
        )
        .mappings()
        .one_or_none()
    )
    return attempt_from_row(dict(row)) if row is not None else None


async def _latest_attempt_row(
    session: AsyncSession,
    run_id: UUID,
) -> dict[str, Any] | None:
    row = (
        (
            await session.execute(
                select(ocr_pipeline_run_attempts_table)
                .where(ocr_pipeline_run_attempts_table.c.run_id == run_id)
                .order_by(ocr_pipeline_run_attempts_table.c.attempt_number.desc())
                .limit(1)
                .with_for_update()
            )
        )
        .mappings()
        .one_or_none()
    )
    return dict(row) if row is not None else None


async def _mark_attempt_lost(
    session: AsyncSession,
    attempt: OcrPipelineRunExecutionAttempt,
    lost_at: datetime,
) -> None:
    await session.execute(
        update(ocr_pipeline_run_attempts_table)
        .where(
            ocr_pipeline_run_attempts_table.c.attempt_id == attempt.attempt_id,
            ocr_pipeline_run_attempts_table.c.status == OcrPipelineRunAttemptStatus.RUNNING.value,
        )
        .values(
            status=OcrPipelineRunAttemptStatus.LOST.value,
            completed_at=lost_at,
            error_code="OCR_PIPELINE_RUN_LEASE_EXPIRED",
        )
    )


async def _close_legacy_running_attempt(
    session: AsyncSession,
    attempt: OcrPipelineRunExecutionAttempt | None,
    record: OcrPipelineRunRecord,
    observed_at: datetime,
) -> None:
    if attempt is None or attempt.status != OcrPipelineRunAttemptStatus.RUNNING:
        return
    completed_at = record.completed_at or observed_at
    await session.execute(
        update(ocr_pipeline_run_attempts_table)
        .where(
            ocr_pipeline_run_attempts_table.c.attempt_id == attempt.attempt_id,
            ocr_pipeline_run_attempts_table.c.status == OcrPipelineRunAttemptStatus.RUNNING.value,
        )
        .values(
            status=OcrPipelineRunAttemptStatus(record.status.value).value,
            completed_at=completed_at,
            error_code=record.error.code if record.error is not None else None,
        )
    )
