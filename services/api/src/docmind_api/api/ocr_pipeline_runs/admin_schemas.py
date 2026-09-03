"""Safe HTTP schemas for administrative OCR run monitoring."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from docmind_api.api.ocr_pipeline_runs.schemas import (
    OcrPipelineRunDiagnosticSchema,
    OcrPipelineRunErrorSchema,
    OcrPipelineRunStepSchema,
)
from docmind_api.domain.ocr_pipeline_runs.models import MetricValue, OcrPipelineRunStatus


class AdminOcrRunAttemptSchema(BaseModel):
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


class AdminOcrRunSummarySchema(BaseModel):
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
    latest_attempt: AdminOcrRunAttemptSchema | None


class AdminOcrRunListData(BaseModel):
    runs: list[AdminOcrRunSummarySchema]


class AdminOcrRunListMeta(BaseModel):
    returned_count: int
    limit: int
    offset: int
    has_more: bool


class AdminOcrRunListEnvelope(BaseModel):
    data: AdminOcrRunListData
    meta: AdminOcrRunListMeta


class AdminOcrRunCancellationAuditSchema(BaseModel):
    requested_at: datetime | None
    requested_by_actor_id: str | None
    requested_by_actor_login: str | None


class AdminOcrRunDetailSchema(BaseModel):
    run: AdminOcrRunSummarySchema
    steps: list[OcrPipelineRunStepSchema]
    metrics: dict[str, MetricValue]
    diagnostics: list[OcrPipelineRunDiagnosticSchema]
    error: OcrPipelineRunErrorSchema | None
    attempts: list[AdminOcrRunAttemptSchema]
    cancellation: AdminOcrRunCancellationAuditSchema


class AdminOcrRunDetailEnvelope(BaseModel):
    data: AdminOcrRunDetailSchema
    meta: dict[str, str] = Field(default_factory=dict)
