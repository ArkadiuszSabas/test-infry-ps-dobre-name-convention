"""Versioned, framework-neutral transport contracts for OCR pipeline events."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)

OCR_DOCUMENT_PROCESSING_TOPIC = "document-processing"
OCR_PROCESSING_RESULTS_TOPIC = "processing-results"
OCR_RUN_REQUESTED_ROUTE = "/internal/events/ocr-run-requested"
OCR_PIPELINE_EVENT_ROUTE = "/internal/events/ocr-pipeline-event"
LLMMAGIC_DISPATCH_REJECTED = "LLMMAGIC_DISPATCH_REJECTED"

_UTC_Z_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$")


def _canonical_uuid(value: str) -> str:
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ValueError("Identifier must be a valid UUID string.") from exc
    if str(parsed) != value:
        raise ValueError("Identifier must use canonical lowercase UUID format.")
    return value


def _utc_z_timestamp(value: str) -> str:
    if _UTC_Z_TIMESTAMP_PATTERN.fullmatch(value) is None:
        raise ValueError("Timestamp must use RFC 3339 UTC format ending in 'Z'.")
    try:
        datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError as exc:
        raise ValueError("Timestamp must be a valid RFC 3339 UTC value.") from exc
    return value


type CanonicalUuidString = Annotated[StrictStr, AfterValidator(_canonical_uuid)]
type UtcZTimestampString = Annotated[StrictStr, AfterValidator(_utc_z_timestamp)]
type CorrelationId = Annotated[
    StrictStr,
    Field(min_length=1, max_length=320, pattern=r"^[^\x00-\x1F\x7F]+$"),
]
type StepId = Annotated[
    StrictStr,
    Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$"),
]
type StepType = Annotated[
    StrictStr,
    Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$"),
]
type ImplementationId = Annotated[
    StrictStr,
    Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$"),
]
type DisplayName = Annotated[
    StrictStr,
    Field(min_length=1, max_length=200, pattern=r"^[^\x00-\x1F\x7F]+$"),
]
type SafeErrorCode = Annotated[
    StrictStr,
    Field(min_length=2, max_length=80, pattern=r"^[A-Z][A-Z0-9_]{1,79}$"),
]
type SafeErrorMessage = Annotated[
    StrictStr,
    Field(min_length=1, max_length=200, pattern=r"^[^\x00-\x1F\x7F]+$"),
]
type SafeMetricKey = Annotated[
    StrictStr,
    Field(min_length=1, max_length=64, pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$"),
]
type MetricValueV1 = StrictBool | StrictInt | StrictFloat


class OcrPipelineEventKindV1(StrEnum):
    """Supported OCR pipeline event kinds."""

    STARTED = "pipeline.started"
    STEP_COMPLETED = "pipeline.step.completed"
    COMPLETED = "pipeline.completed"
    FAILED = "pipeline.failed"


class OcrPipelineStatusV1(StrEnum):
    """Pipeline status values carried by execution events."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class OcrPipelineStepStatusV1(StrEnum):
    """Status values for one step in a progress snapshot."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class OcrDispatchDispositionV1(StrEnum):
    """API disposition returned to the Worker dispatch boundary."""

    DISPATCHABLE = "dispatchable"
    ACTIVE = "active"
    TERMINAL = "terminal"
    DELETED = "deleted"


class OcrPipelineRunAcceptanceStatusV1(StrEnum):
    """LLM Magic admission result for an accepted run."""

    ACCEPTED = "accepted"


class OcrDispatchFailureCodeV1(StrEnum):
    """Safe permanent dispatch rejection codes."""

    LLMMAGIC_DISPATCH_REJECTED = LLMMAGIC_DISPATCH_REJECTED


class _OcrTransportModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        allow_inf_nan=False,
    )


class OcrRunRequestedV1(_OcrTransportModel):
    """Small API-owned request event published through the run outbox."""

    run_id: CanonicalUuidString
    document_id: CanonicalUuidString
    correlation_id: CorrelationId
    requested_at: UtcZTimestampString


class OcrPipelineSafeErrorV1(_OcrTransportModel):
    """Bounded, display-safe error without exception or provider payload fields."""

    code: SafeErrorCode
    message: SafeErrorMessage


class OcrPipelineStepSnapshotV1(_OcrTransportModel):
    """One step in the complete current pipeline progress snapshot."""

    step_id: StepId
    display_name: DisplayName
    step_type: StepType
    implementation_id: ImplementationId
    status: OcrPipelineStepStatusV1
    duration_ms: Annotated[StrictInt, Field(ge=0)] | None = None
    metrics: dict[SafeMetricKey, MetricValueV1] = Field(default_factory=dict)
    error: OcrPipelineSafeErrorV1 | None = None


class OcrPipelineEventV1(_OcrTransportModel):
    """Shared progress and terminal-notification envelope published by LLM Magic."""

    kind: OcrPipelineEventKindV1
    event_id: CanonicalUuidString
    run_id: CanonicalUuidString
    document_id: CanonicalUuidString
    attempt_id: CanonicalUuidString
    fencing_token: Annotated[StrictInt, Field(ge=1)]
    sequence: Annotated[StrictInt, Field(ge=1)]
    pipeline_id: CanonicalUuidString
    pipeline_status: OcrPipelineStatusV1
    steps: tuple[OcrPipelineStepSnapshotV1, ...] = Field(min_length=1)
    completed_step_id: StepId | None = None
    error: OcrPipelineSafeErrorV1 | None = None

    @model_validator(mode="after")
    def validate_event_variant(self) -> Self:
        """Reject kind/status/sequence combinations outside the frozen V1 protocol."""

        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Pipeline event steps must use unique step_id values.")

        if self.kind is OcrPipelineEventKindV1.STARTED:
            if self.sequence != 1:
                raise ValueError("pipeline.started must use sequence=1.")
            if self.pipeline_status is not OcrPipelineStatusV1.RUNNING:
                raise ValueError("pipeline.started must use pipeline_status='running'.")
            if self.completed_step_id is not None:
                raise ValueError("pipeline.started cannot identify a completed step.")
            return self

        if self.sequence == 1:
            raise ValueError("Only pipeline.started may use sequence=1.")

        if self.kind is OcrPipelineEventKindV1.STEP_COMPLETED:
            if self.pipeline_status is not OcrPipelineStatusV1.RUNNING:
                raise ValueError("pipeline.step.completed must use pipeline_status='running'.")
            if self.completed_step_id is None:
                raise ValueError("pipeline.step.completed requires completed_step_id.")
            if not any(step.step_id == self.completed_step_id for step in self.steps):
                raise ValueError("completed_step_id must identify a step in the snapshot.")
            completed_step = next(
                step for step in self.steps if step.step_id == self.completed_step_id
            )
            if completed_step.status not in {
                OcrPipelineStepStatusV1.SUCCEEDED,
                OcrPipelineStepStatusV1.FAILED,
                OcrPipelineStepStatusV1.SKIPPED,
            }:
                raise ValueError("completed_step_id must identify a completed step.")
            return self

        if self.completed_step_id is not None:
            raise ValueError("Terminal events cannot identify a completed step.")

        if self.kind is OcrPipelineEventKindV1.COMPLETED:
            if self.pipeline_status not in {
                OcrPipelineStatusV1.SUCCEEDED,
                OcrPipelineStatusV1.PARTIAL_FAILED,
            }:
                raise ValueError("pipeline.completed must use succeeded or partial_failed status.")
            if any(
                step.status
                in {
                    OcrPipelineStepStatusV1.PENDING,
                    OcrPipelineStepStatusV1.RUNNING,
                }
                for step in self.steps
            ):
                raise ValueError("pipeline.completed requires terminal step statuses.")
            has_failed_step = any(
                step.status is OcrPipelineStepStatusV1.FAILED for step in self.steps
            )
            if self.pipeline_status is OcrPipelineStatusV1.SUCCEEDED and has_failed_step:
                raise ValueError("A succeeded pipeline cannot contain a failed step.")
            if self.pipeline_status is OcrPipelineStatusV1.PARTIAL_FAILED and not has_failed_step:
                raise ValueError("A partial_failed pipeline requires a failed step.")
            return self

        if self.kind is OcrPipelineEventKindV1.FAILED:
            if self.pipeline_status is not OcrPipelineStatusV1.FAILED:
                raise ValueError("pipeline.failed must use pipeline_status='failed'.")
            return self

        raise ValueError("Unsupported OCR pipeline event kind.")


class DispatchFailedV1(_OcrTransportModel):
    """Permanent Worker-to-API dispatch rejection report."""

    fencing_token: Annotated[StrictInt, Field(ge=1)]
    code: OcrDispatchFailureCodeV1


class OcrPipelineRunAcceptedV1(_OcrTransportModel):
    """Data payload returned after LLM Magic accepts an in-process run."""

    run_id: CanonicalUuidString
    attempt_id: CanonicalUuidString
    status: OcrPipelineRunAcceptanceStatusV1
