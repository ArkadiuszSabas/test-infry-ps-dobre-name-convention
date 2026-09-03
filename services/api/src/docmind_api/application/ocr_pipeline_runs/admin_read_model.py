"""Administrative read model for cross-document OCR run monitoring."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from docmind_api.application.ocr_pipeline_runs.errors import OcrPipelineRunNotFoundError
from docmind_api.domain.ocr_pipeline_runs.models import (
    MetricValue,
    OcrPipelineRunDiagnostic,
    OcrPipelineRunError,
    OcrPipelineRunStatus,
    OcrPipelineRunStep,
)


@dataclass(frozen=True, slots=True)
class AdminOcrRunAttempt:
    """Safe operational projection of one execution attempt."""

    attempt_id: UUID
    attempt_number: int
    status: str
    started_at: datetime
    invocation_started_at: datetime | None
    last_renewed_at: datetime
    lease_expires_at: datetime
    completed_at: datetime | None
    error_code: str | None
    execution_deadline_at: datetime | None
    cancellation_deadline_at: datetime | None
    last_event_sequence: int


@dataclass(frozen=True, slots=True)
class AdminOcrRunSummary:
    """Bounded list projection without OCR result content."""

    id: UUID
    document_id: UUID
    document_name: str
    document_type_id: UUID
    document_type_name: str
    pipeline_id: UUID
    pipeline_name: str | None
    pipeline_version: int
    status: OcrPipelineRunStatus
    current_step_name: str | None
    current_step_status: str | None
    completed_step_count: int
    total_step_count: int
    started_by_actor_id: str | None
    started_by_actor_type: str
    started_by_actor_login: str | None
    document_source: str | None
    document_connector: str | None
    connector_instance_id: str | None
    connector_display_name: str | None
    connector_correlation_id: str | None
    created_at: datetime
    started_at: datetime | None
    updated_at: datetime
    completed_at: datetime | None
    latest_attempt: AdminOcrRunAttempt | None


@dataclass(frozen=True, slots=True)
class AdminOcrRunDetail:
    """Safe run detail with diagnostics and execution history."""

    run: AdminOcrRunSummary
    steps: tuple[OcrPipelineRunStep, ...]
    metrics: Mapping[str, MetricValue]
    diagnostics: tuple[OcrPipelineRunDiagnostic, ...]
    error: OcrPipelineRunError | None
    attempts: tuple[AdminOcrRunAttempt, ...]
    cancellation_requested_at: datetime | None
    cancellation_requested_by_actor_id: str | None
    cancellation_requested_by_actor_login: str | None


@dataclass(frozen=True, slots=True)
class AdminOcrRunFilters:
    """Validated transport filters passed to the persistence adapter."""

    view: str
    statuses: tuple[OcrPipelineRunStatus, ...]
    pipeline_id: UUID | None
    document_type_id: UUID | None
    source: str | None
    connector: str | None
    created_from: datetime | None
    created_to: datetime | None
    updated_before: datetime | None
    search: str | None
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class AdminOcrRunPage:
    """One stable page of administrative OCR runs."""

    runs: tuple[AdminOcrRunSummary, ...]
    limit: int
    offset: int
    has_more: bool


class AdminOcrRunReadRepository(Protocol):
    """Persistence port for administrative OCR run reads."""

    async def list_runs(self, filters: AdminOcrRunFilters) -> AdminOcrRunPage: ...

    async def get_run(self, run_id: UUID) -> AdminOcrRunDetail | None: ...


class AdminOcrRunReadService:
    """Application boundary for the administrative run console."""

    def __init__(self, repository: AdminOcrRunReadRepository) -> None:
        self._repository = repository

    async def list_runs(self, filters: AdminOcrRunFilters) -> AdminOcrRunPage:
        return await self._repository.list_runs(filters)

    async def get_run(self, run_id: UUID) -> AdminOcrRunDetail:
        detail = await self._repository.get_run(run_id)
        if detail is None:
            raise OcrPipelineRunNotFoundError(run_id=run_id)
        return detail
