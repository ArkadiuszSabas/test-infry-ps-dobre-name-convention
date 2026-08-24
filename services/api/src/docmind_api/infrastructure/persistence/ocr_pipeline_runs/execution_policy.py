"""Pure acquisition policy for persisted OCR pipeline execution attempts."""

from datetime import datetime

from docmind_api.domain.ocr_pipeline_runs.models import (
    OcrPipelineRunAcquireDisposition,
    OcrPipelineRunAcquireReason,
    OcrPipelineRunAttemptStatus,
    OcrPipelineRunExecutionAttempt,
    OcrPipelineRunRecord,
    OcrPipelineRunStatus,
)


def acquire_reason(
    record: OcrPipelineRunRecord,
    latest: OcrPipelineRunExecutionAttempt | None,
    acquired_at: datetime,
) -> OcrPipelineRunAcquireReason | None:
    if record.status == OcrPipelineRunStatus.PENDING and latest is None:
        return OcrPipelineRunAcquireReason.NEW
    if record.status == OcrPipelineRunStatus.FAILED and (
        latest is None or latest.status == OcrPipelineRunAttemptStatus.FAILED
    ):
        return OcrPipelineRunAcquireReason.RETRY
    if (
        record.status == OcrPipelineRunStatus.RUNNING
        and latest is not None
        and latest.status == OcrPipelineRunAttemptStatus.RUNNING
        and latest.invocation_started_at is None
        and latest.lease_expires_at <= acquired_at
    ):
        return OcrPipelineRunAcquireReason.EXPIRED_LEASE_TAKEOVER
    return None


def non_acquired_disposition(
    record: OcrPipelineRunRecord,
    latest: OcrPipelineRunExecutionAttempt | None,
    acquired_at: datetime,
    max_attempts: int,
) -> OcrPipelineRunAcquireDisposition:
    if (
        record.status == OcrPipelineRunStatus.RUNNING
        and latest is not None
        and latest.status == OcrPipelineRunAttemptStatus.RUNNING
        and latest.lease_expires_at > acquired_at
    ):
        return OcrPipelineRunAcquireDisposition.ACTIVE_DUPLICATE
    if (
        record.status == OcrPipelineRunStatus.FAILED
        and latest is not None
        and latest.attempt_number >= max_attempts
    ):
        return OcrPipelineRunAcquireDisposition.RETRY_EXHAUSTED
    return OcrPipelineRunAcquireDisposition.AMBIGUOUS
