"""Application ports for OCR pipeline run workflows."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from docmind_api.domain.ocr_pipeline_runs.models import (
    JsonObject,
    MetricValue,
    OcrPipelineRunDocument,
    OcrPipelineRunList,
    OcrPipelineRunRecord,
    OcrPipelineRunStatus,
    RunnableOcrPipelineSnapshot,
)
from docmind_api.domain.ocr_pipeline_runs.value_objects import (
    OcrPipelineRunDiagnostic,
    OcrPipelineRunError,
    OcrPipelineRunStep,
)


@dataclass(frozen=True, slots=True)
class OcrPipelineRunLimits:
    """Limits protecting event-driven OCR pipeline run creation."""

    max_content_bytes: int
    max_step_count: int


class Clock(Protocol):
    """Port for obtaining audit timestamps."""

    def now(self) -> datetime: ...


class OcrPipelineRunIdFactory(Protocol):
    """Port for creating OCR pipeline run identifiers."""

    def new_id(self) -> UUID: ...


class OcrPipelineRunDocumentReader(Protocol):
    """Port for reading document data required by OCR runs."""

    async def get_run_document(self, document_id: UUID) -> OcrPipelineRunDocument | None: ...


class PublishedOcrPipelineSnapshotReader(Protocol):
    """Port for selecting published pipeline snapshots for execution."""

    async def get_default_published(self) -> RunnableOcrPipelineSnapshot | None: ...

    async def get_published(
        self,
        pipeline_id: UUID,
    ) -> RunnableOcrPipelineSnapshot | None: ...

    async def list_published(self) -> tuple[RunnableOcrPipelineSnapshot, ...]: ...


class OcrPipelineRunRepository(Protocol):
    """Port implemented by OCR pipeline run persistence adapters."""

    async def add(self, record: OcrPipelineRunRecord) -> bool: ...

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


class OcrRunOutboxRepository(Protocol):
    """Persistence port for the durable OCR request outbox."""

    async def claim_request_outbox(self, *, limit: int) -> tuple[OcrRunOutboxRecord, ...]: ...

    async def mark_request_outbox_published(
        self,
        outbox_id: UUID,
        *,
        published_at: datetime,
    ) -> bool: ...


class OcrEventControlRepository(Protocol):
    """Persistence port for event-mode dispatch and progress fencing."""

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
    ) -> OcrEventDispatchResult | None: ...

    async def fail_event_dispatch(
        self,
        run_id: UUID,
        attempt_id: UUID,
        *,
        fencing_token: int,
        error_code: str,
    ) -> bool: ...

    async def defer_event_dispatch(
        self,
        run_id: UUID,
        attempt_id: UUID,
        *,
        fencing_token: int,
        defer_seconds: float,
    ) -> bool: ...

    async def reconcile_event_executions(self, *, defer_seconds: float) -> int: ...

    async def request_cancellation(
        self,
        run_id: UUID,
        *,
        actor_id: str,
        actor_login: str | None,
        cancellation_timeout_seconds: float,
    ) -> OcrCancellationResult | None: ...

    async def complete_cancellation(
        self, run_id: UUID, attempt_id: UUID, *, fencing_token: int, error_code: str | None = None
    ) -> str: ...

    async def record_cancellation_dispatch_failure(
        self,
        run_id: UUID,
        attempt_id: UUID,
        *,
        fencing_token: int,
        error_code: str,
    ) -> str: ...

    async def reconcile_cancellations(self) -> int: ...

    async def apply_pipeline_event(self, event: Any) -> str: ...

    async def complete_event_run(
        self,
        run_id: UUID,
        attempt_id: UUID,
        completion: OcrEventCompletion,
    ) -> str: ...


class OcrEventRunCompleter(Protocol):
    """Completes an event-mode run and performs post-commit follow-up work."""

    async def complete(
        self,
        run_id: UUID,
        attempt_id: UUID,
        completion: OcrEventCompletion,
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class OcrRunOutboxRecord:
    """One claimed, stable-id OCR run request awaiting publication."""

    id: UUID
    topic: str
    event_type: str
    payload: dict[str, object]
    publish_attempts: int


@dataclass(frozen=True, slots=True)
class OcrEventDispatchResult:
    disposition: str
    attempt_id: UUID | None = None
    attempt_number: int | None = None
    fencing_token: int | None = None
    execution_deadline_at: datetime | None = None
    run_request: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class OcrEventCompletion:
    """Terminal data submitted by LLM Magic for one fenced event-mode attempt."""

    document_id: UUID
    fencing_token: int
    status: OcrPipelineRunStatus
    steps: tuple[OcrPipelineRunStep, ...]
    metrics: Mapping[str, MetricValue]
    diagnostics: tuple[OcrPipelineRunDiagnostic, ...]
    error: OcrPipelineRunError | None
    result_payload: JsonObject | None


@dataclass(frozen=True, slots=True)
class OcrCancellationResult:
    disposition: str
    record: OcrPipelineRunRecord
