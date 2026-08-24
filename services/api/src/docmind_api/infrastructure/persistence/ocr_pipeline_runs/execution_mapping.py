"""Mapping helpers for persisted OCR pipeline execution ownership."""

from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import ColumnElement

from docmind_api.domain.ocr_pipeline_runs.models import (
    OcrPipelineRunAcquireReason,
    OcrPipelineRunAttemptStatus,
    OcrPipelineRunDiagnostic,
    OcrPipelineRunDiagnosticSeverity,
    OcrPipelineRunError,
    OcrPipelineRunExecutionAttempt,
    OcrPipelineRunExecutionLease,
    OcrPipelineRunRecord,
    OcrPipelineRunStatus,
    OcrPipelineRunStepStatus,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.mappers import record_to_values
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.tables import (
    ocr_pipeline_run_attempts_table,
)


def reset_record_for_attempt(
    record: OcrPipelineRunRecord,
    lease: OcrPipelineRunExecutionLease,
    reason: OcrPipelineRunAcquireReason,
) -> OcrPipelineRunRecord:
    metrics = {
        key: value
        for key, value in record.metrics.items()
        if key in {"document_size_bytes", "execution_lease_takeover_count"}
    }
    metrics["execution_attempt_count"] = lease.attempt_number
    if reason == OcrPipelineRunAcquireReason.EXPIRED_LEASE_TAKEOVER:
        current = metrics.get("execution_lease_takeover_count", 0)
        metrics["execution_lease_takeover_count"] = (
            int(current) + 1 if isinstance(current, int) and not isinstance(current, bool) else 1
        )
    return replace(
        record,
        status=OcrPipelineRunStatus.RUNNING,
        steps=tuple(
            replace(
                step,
                status=OcrPipelineRunStepStatus.PENDING,
                duration_seconds=None,
                metrics={},
                error=None,
            )
            for step in record.steps
        ),
        metrics=metrics,
        diagnostics=(),
        error=None,
        result_payload=None,
        started_at=record.started_at or lease.acquired_at,
        completed_at=None,
        updated_at=lease.acquired_at,
    )


def exhausted_record(
    record: OcrPipelineRunRecord,
    *,
    completed_at: datetime,
) -> OcrPipelineRunRecord:
    code = "OCR_PIPELINE_RUN_ATTEMPTS_EXHAUSTED"
    message = "OCR pipeline run attempts are exhausted."
    return replace(
        record,
        status=OcrPipelineRunStatus.FAILED,
        diagnostics=(
            *record.diagnostics,
            OcrPipelineRunDiagnostic(
                severity=OcrPipelineRunDiagnosticSeverity.ERROR,
                code=code,
                message=message,
            ),
        ),
        error=OcrPipelineRunError(code=code, message=message),
        completed_at=completed_at,
        updated_at=completed_at,
    )


def mutable_run_values(record: OcrPipelineRunRecord) -> dict[str, object]:
    values = record_to_values(record)
    mutable_names = {
        "status",
        "steps",
        "metrics",
        "diagnostics",
        "error",
        "result_payload",
        "updated_at",
        "started_at",
        "completed_at",
    }
    return {name: value for name, value in values.items() if name in mutable_names}


def lease_identity_predicates(
    lease: OcrPipelineRunExecutionLease,
) -> tuple[ColumnElement[bool], ...]:
    return (
        ocr_pipeline_run_attempts_table.c.attempt_id == lease.attempt_id,
        ocr_pipeline_run_attempts_table.c.run_id == lease.run_id,
        ocr_pipeline_run_attempts_table.c.owner_token == lease.owner_token,
        ocr_pipeline_run_attempts_table.c.attempt_number == lease.attempt_number,
        ocr_pipeline_run_attempts_table.c.fencing_token == lease.fencing_token,
    )


def lease_from_row(row: Mapping[str, Any]) -> OcrPipelineRunExecutionLease:
    return OcrPipelineRunExecutionLease(
        run_id=cast(UUID, row["run_id"]),
        attempt_id=cast(UUID, row["attempt_id"]),
        owner_token=cast(UUID, row["owner_token"]),
        attempt_number=int(row["attempt_number"]),
        fencing_token=int(row["fencing_token"]),
        acquired_at=cast(datetime, row["started_at"]),
        last_renewed_at=cast(datetime, row["last_renewed_at"]),
        lease_expires_at=cast(datetime, row["lease_expires_at"]),
    )


def attempt_from_row(row: Mapping[str, Any]) -> OcrPipelineRunExecutionAttempt:
    return OcrPipelineRunExecutionAttempt(
        run_id=cast(UUID, row["run_id"]),
        attempt_id=cast(UUID, row["attempt_id"]),
        owner_token=cast(UUID, row["owner_token"]),
        attempt_number=int(row["attempt_number"]),
        fencing_token=int(row["fencing_token"]),
        status=OcrPipelineRunAttemptStatus(str(row["status"])),
        started_at=cast(datetime, row["started_at"]),
        invocation_started_at=cast(datetime | None, row["invocation_started_at"]),
        last_renewed_at=cast(datetime, row["last_renewed_at"]),
        lease_expires_at=cast(datetime, row["lease_expires_at"]),
        completed_at=cast(datetime | None, row["completed_at"]),
        error_code=cast(str | None, row["error_code"]),
    )
