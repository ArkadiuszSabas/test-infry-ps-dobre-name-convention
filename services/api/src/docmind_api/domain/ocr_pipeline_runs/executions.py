"""Execution-attempt ownership models for OCR pipeline runs."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from docmind_api.domain.ocr_pipeline_runs.records import OcrPipelineRunRecord


class OcrPipelineRunAttemptStatus(StrEnum):
    """Persisted state of one physical execution attempt."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"
    INDETERMINATE = "indeterminate"
    LOST = "lost"


class OcrPipelineRunAcquireDisposition(StrEnum):
    """Outcome of an atomic execution-ownership request."""

    ACQUIRED = "acquired"
    ACTIVE_DUPLICATE = "active_duplicate"
    RESULT_REUSED = "result_reused"
    RETRY_EXHAUSTED = "retry_exhausted"
    AMBIGUOUS = "ambiguous"


class OcrPipelineRunAcquireReason(StrEnum):
    """Reason why a process received a new execution lease."""

    NEW = "new"
    RETRY = "retry"
    EXPIRED_LEASE_TAKEOVER = "expired_lease_takeover"


@dataclass(frozen=True, slots=True)
class OcrPipelineRunExecutionLease:
    """Fenced ownership granted for one physical execution attempt."""

    run_id: UUID
    attempt_id: UUID
    owner_token: UUID
    attempt_number: int
    fencing_token: int
    acquired_at: datetime
    last_renewed_at: datetime
    lease_expires_at: datetime

    def __post_init__(self) -> None:
        if self.attempt_number < 1:
            raise ValueError("OCR pipeline run attempt number must be positive.")
        if self.fencing_token < 1:
            raise ValueError("OCR pipeline run fencing token must be positive.")
        if self.last_renewed_at < self.acquired_at:
            raise ValueError("OCR pipeline run renewal cannot precede acquisition.")
        if self.lease_expires_at <= self.last_renewed_at:
            raise ValueError("OCR pipeline run lease must expire after its renewal.")


@dataclass(frozen=True, slots=True)
class OcrPipelineRunAcquireResult:
    """Result of atomically acquiring or observing one logical run."""

    disposition: OcrPipelineRunAcquireDisposition
    record: OcrPipelineRunRecord
    lease: OcrPipelineRunExecutionLease | None = None
    reason: OcrPipelineRunAcquireReason | None = None

    def __post_init__(self) -> None:
        acquired = self.disposition == OcrPipelineRunAcquireDisposition.ACQUIRED
        if acquired != (self.lease is not None and self.reason is not None):
            raise ValueError("Only acquired OCR pipeline runs may carry a lease and reason.")


@dataclass(frozen=True, slots=True)
class OcrPipelineRunExecutionAttempt:
    """Safe persisted history for one physical execution attempt."""

    run_id: UUID
    attempt_id: UUID
    owner_token: UUID
    attempt_number: int
    fencing_token: int
    status: OcrPipelineRunAttemptStatus
    started_at: datetime
    invocation_started_at: datetime | None
    last_renewed_at: datetime
    lease_expires_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None
