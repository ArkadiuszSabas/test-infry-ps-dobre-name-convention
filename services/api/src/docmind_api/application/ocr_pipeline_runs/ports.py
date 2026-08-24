"""Application ports for OCR pipeline run workflows."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from docmind_api.domain.ocr_pipeline_runs.models import (
    OcrPipelineRunAcquireReason,
    OcrPipelineRunAcquireResult,
    OcrPipelineRunDocument,
    OcrPipelineRunExecutionAttempt,
    OcrPipelineRunExecutionLease,
    OcrPipelineRunList,
    OcrPipelineRunRecord,
    RunnableOcrPipelineSnapshot,
)


@dataclass(frozen=True, slots=True)
class DirectOcrPipelineRunLimits:
    """Limits protecting the temporary direct API-to-LLM Magic run path."""

    max_content_bytes: int
    max_step_count: int


@dataclass(frozen=True, slots=True)
class OcrPipelineRunExecutionPolicy:
    """Retry and lease policy for physical pipeline executions."""

    max_attempts: int
    lease_duration_seconds: float
    lease_renewal_interval_seconds: float

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("OCR pipeline run max attempts must be positive.")
        if self.lease_duration_seconds <= 0:
            raise ValueError("OCR pipeline run lease duration must be positive.")
        if self.lease_renewal_interval_seconds <= 0:
            raise ValueError("OCR pipeline run lease renewal interval must be positive.")
        if self.lease_renewal_interval_seconds >= self.lease_duration_seconds:
            raise ValueError("OCR pipeline run renewal interval must be shorter than its lease.")


@dataclass(frozen=True, slots=True)
class OcrPipelineRunInvocationContext:
    """Physical execution identity forwarded to the OCR observability boundary."""

    attempt_id: UUID
    attempt_number: int
    fencing_token: int
    acquisition_reason: OcrPipelineRunAcquireReason


class Clock(Protocol):
    """Port for obtaining audit timestamps."""

    def now(self) -> datetime: ...


class OcrPipelineRunIdFactory(Protocol):
    """Port for creating OCR pipeline run identifiers."""

    def new_id(self) -> UUID: ...


class OcrPipelineRunExecutionIdentityFactory(Protocol):
    """Port for distinct attempt and ownership identifiers."""

    def new_attempt_id(self) -> UUID: ...

    def new_owner_token(self) -> UUID: ...


class OcrPipelineRunDocumentReader(Protocol):
    """Port for reading document data required by direct OCR runs."""

    async def get_run_document(self, document_id: UUID) -> OcrPipelineRunDocument | None: ...


class PublishedOcrPipelineSnapshotReader(Protocol):
    """Port for selecting published pipeline snapshots for execution."""

    async def get_default_published(self) -> RunnableOcrPipelineSnapshot | None: ...


class OcrPipelineRunRepository(Protocol):
    """Port implemented by OCR pipeline run persistence adapters."""

    async def add(self, record: OcrPipelineRunRecord) -> bool: ...

    async def acquire_execution(
        self,
        run_id: UUID | str,
        *,
        attempt_id: UUID,
        owner_token: UUID,
        acquired_at: datetime,
        lease_expires_at: datetime,
        max_attempts: int,
    ) -> OcrPipelineRunAcquireResult | None: ...

    async def renew_execution(
        self,
        lease: OcrPipelineRunExecutionLease,
        *,
        renewed_at: datetime,
        lease_expires_at: datetime,
    ) -> OcrPipelineRunExecutionLease | None: ...

    async def mark_execution_invocation_started(
        self,
        lease: OcrPipelineRunExecutionLease,
    ) -> bool: ...

    async def save_execution_result(
        self,
        lease: OcrPipelineRunExecutionLease,
        record: OcrPipelineRunRecord,
        *,
        completed_at: datetime,
    ) -> bool: ...

    async def record_execution_error(
        self,
        lease: OcrPipelineRunExecutionLease,
        *,
        error_code: str,
        updated_at: datetime,
    ) -> bool: ...

    async def fail_stale_executions(self, *, stale_after_seconds: float) -> int: ...

    async def get_execution_attempt(
        self,
        attempt_id: UUID,
    ) -> OcrPipelineRunExecutionAttempt | None: ...

    async def get_by_id(self, run_id: UUID | str) -> OcrPipelineRunRecord | None: ...

    async def get_active_by_document_id(
        self,
        document_id: UUID,
    ) -> OcrPipelineRunRecord | None: ...

    async def list_by_document_id(
        self,
        document_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> OcrPipelineRunList: ...


class OcrPipelineRunInvoker(Protocol):
    """Port implemented by the LLM Magic direct run adapter."""

    async def invoke_run(
        self,
        record: OcrPipelineRunRecord,
        context: OcrPipelineRunInvocationContext,
    ) -> OcrPipelineRunRecord: ...


OcrPipelineRunDispatch = Callable[[UUID], Awaitable[None]]


class OcrPipelineRunDispatcher(Protocol):
    """Dispatches one persisted OCR pipeline run."""

    async def dispatch(self, run_id: UUID) -> None: ...


class OcrPipelineRunScheduler(Protocol):
    """Schedules persisted OCR runs outside an HTTP request lifecycle."""

    def schedule(self, dispatch: OcrPipelineRunDispatch, run_id: UUID) -> None: ...
