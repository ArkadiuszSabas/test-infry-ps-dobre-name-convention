"""HTTP schemas for OCR pipeline run endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from docmind_api.domain.ocr_pipeline_runs.models import (
    MetricValue,
    OcrPipelineRunDiagnosticSeverity,
    OcrPipelineRunResultAvailability,
    OcrPipelineRunStatus,
    OcrPipelineRunStepStatus,
)


class OcrPipelineRunErrorSchema(BaseModel):
    """HTTP schema for safe OCR pipeline run errors."""

    code: str
    message: str


class StartOcrPipelineRunRequest(BaseModel):
    """Optional published pipeline selection for a new OCR run."""

    model_config = ConfigDict(extra="forbid")

    pipeline_id: UUID | None = None


class PublishedOcrPipelineOptionSchema(BaseModel):
    """Published pipeline available for starting a new OCR run."""

    id: UUID
    name: str
    published_version: int
    is_default: bool


class PublishedOcrPipelineOptionListSchema(BaseModel):
    """Published pipeline options available to OCR operators."""

    pipelines: list[PublishedOcrPipelineOptionSchema]


class PublishedOcrPipelineOptionListMeta(BaseModel):
    """Metadata for published OCR pipeline options."""

    total_count: int


class PublishedOcrPipelineOptionListEnvelope(BaseModel):
    """Standard API envelope for published OCR pipeline options."""

    data: PublishedOcrPipelineOptionListSchema
    meta: PublishedOcrPipelineOptionListMeta


class OcrPipelineRunDiagnosticSchema(BaseModel):
    """HTTP schema for safe OCR pipeline run diagnostics."""

    severity: OcrPipelineRunDiagnosticSeverity
    code: str
    message: str
    step_id: str | None
    path: str | None


class OcrPipelineRunStepSchema(BaseModel):
    """HTTP schema for one OCR pipeline run step status."""

    step_id: str
    step_type: str
    implementation_id: str
    display_name: str
    status: OcrPipelineRunStepStatus
    duration_seconds: float | None
    metrics: dict[str, MetricValue]
    error: OcrPipelineRunErrorSchema | None


class OcrPipelineRunOcrResultPageSchema(BaseModel):
    """HTTP schema for one safe OCR result page."""

    page_number: int
    status: str
    text: str
    text_truncated: bool
    lines: list[str]
    lines_truncated: bool
    confidence: float | None
    warning_codes: list[str]
    error_code: str | None
    fallback_used: bool
    fallback_reason_codes: list[str]
    primary_error_code: str | None


class OcrPipelineRunOcrKeyValuePairSchema(BaseModel):
    """HTTP schema for one safe provider-detected key-value pair."""

    key: str
    value: str
    key_truncated: bool
    value_truncated: bool
    confidence: float | None
    page_number: int
    bounding_polygon: list[float]
    order_index: int
    source: str


class OcrPipelineRunContextResolutionQualitySchema(BaseModel):
    """HTTP schema for safe Context Resolver quality metrics."""

    resolved_attribute_count: int
    review_required_attribute_count: int
    missing_required_attribute_count: int
    missing_attribute_count: int
    low_confidence_attribute_count: int
    conflicting_attribute_count: int


class OcrPipelineRunContextResolutionSourceSchema(BaseModel):
    """HTTP schema for one safe Context Resolver source reference."""

    kind: str
    order_index: int | None = Field(default=None, ge=0)
    page_number: int | None = None
    line_number: int | None = None
    key_value_index: int | None = None
    confidence: float | None = None
    bounding_polygon: list[Annotated[float, Field(ge=0, le=1)]] | None = Field(
        default=None,
        min_length=8,
        max_length=16,
    )

    @field_validator("bounding_polygon")
    @classmethod
    def require_complete_coordinate_pairs(
        cls,
        value: list[float] | None,
    ) -> list[float] | None:
        if value is not None and len(value) % 2 != 0:
            raise ValueError("bounding_polygon must contain complete x/y coordinate pairs")
        return value


class OcrPipelineRunContextResolutionAttributeSchema(BaseModel):
    """HTTP schema for one resolved document attribute."""

    document_type_id: str | None = None
    attribute_external_id: str
    attribute_id: str | None = None
    display_name: str
    value_type: str | None = None
    required: bool
    value: str | None = None
    confidence_score: float | None = None
    status: str
    requires_review: bool
    sources: list[OcrPipelineRunContextResolutionSourceSchema]
    reason_codes: list[str]
    consistency_status: str | None = None
    compared_values: list[str] = Field(default_factory=list[str])
    compared_key_value_pages: list[int] = Field(default_factory=list[int])
    compared_key_value_indexes: list[int] = Field(default_factory=list[int])
    confidence_before: float | None = None
    confidence_after: float | None = None


class OcrPipelineRunContextResolutionResultSchema(BaseModel):
    """HTTP schema for safe Context Resolver result content."""

    schema_version: int
    status: str
    document_type_id: str | None = None
    total_attribute_count: int
    quality: OcrPipelineRunContextResolutionQualitySchema
    attributes: list[OcrPipelineRunContextResolutionAttributeSchema]


class OcrPipelineRunOcrResultSchema(BaseModel):
    """HTTP schema for safe OCR result content."""

    status: str
    provider_id: str
    model_id: str
    total_page_count: int
    succeeded_page_count: int
    failed_page_count: int
    average_confidence: float | None
    low_confidence_page_count: int
    warning_count: int
    pages_truncated: bool
    pages: list[OcrPipelineRunOcrResultPageSchema]
    key_value_pairs_truncated: bool = False
    key_value_pairs: list[OcrPipelineRunOcrKeyValuePairSchema] = Field(
        default_factory=list[OcrPipelineRunOcrKeyValuePairSchema],
    )
    context_resolution_result: OcrPipelineRunContextResolutionResultSchema | None = None


class OcrPipelineRunSchema(BaseModel):
    """HTTP schema for an OCR pipeline run."""

    id: UUID
    document_id: UUID
    pipeline_id: UUID
    pipeline_name: str | None
    pipeline_version: int
    status: OcrPipelineRunStatus
    result_availability: OcrPipelineRunResultAvailability
    result_unavailable_reason_code: str | None
    steps: list[OcrPipelineRunStepSchema]
    metrics: dict[str, MetricValue]
    diagnostics: list[OcrPipelineRunDiagnosticSchema]
    error: OcrPipelineRunErrorSchema | None
    catalog_version: str | None
    catalog_hash: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class OcrPipelineRunEnvelope(BaseModel):
    """Standard API response envelope for one OCR pipeline run."""

    data: OcrPipelineRunSchema
    meta: dict[str, str] = Field(default_factory=dict)


class OcrPipelineRunListSchema(BaseModel):
    """HTTP schema for document OCR pipeline run history."""

    runs: list[OcrPipelineRunSchema]


class OcrPipelineRunListMeta(BaseModel):
    """HTTP metadata for document OCR pipeline run history."""

    document_id: UUID
    returned_count: int
    limit: int
    offset: int
    has_more: bool


class OcrPipelineRunListEnvelope(BaseModel):
    """Standard API response envelope for document OCR pipeline run history."""

    data: OcrPipelineRunListSchema
    meta: OcrPipelineRunListMeta


class OcrPipelineRunResultSchema(BaseModel):
    """HTTP schema for safe OCR pipeline run result polling."""

    run: OcrPipelineRunSchema
    result_available: bool
    unavailable_reason_code: str | None
    result: OcrPipelineRunOcrResultSchema | None


class OcrPipelineRunResultEnvelope(BaseModel):
    """Standard API response envelope for a safe OCR pipeline run result."""

    data: OcrPipelineRunResultSchema
    meta: dict[str, str] = Field(default_factory=dict)


class OcrPipelineRunCompletionSchema(BaseModel):
    """Bounded terminal result submitted by LLM Magic for a fenced attempt."""

    document_id: UUID
    fencing_token: int = Field(ge=1)
    status: OcrPipelineRunStatus
    steps: list[OcrPipelineRunStepSchema] = Field(default_factory=list[OcrPipelineRunStepSchema])
    metrics: dict[str, MetricValue] = Field(default_factory=dict)
    diagnostics: list[OcrPipelineRunDiagnosticSchema] = Field(
        default_factory=list[OcrPipelineRunDiagnosticSchema],
    )
    error: OcrPipelineRunErrorSchema | None = None
    result: OcrPipelineRunOcrResultSchema | None = None

    @model_validator(mode="after")
    def validate_terminal_result(self) -> OcrPipelineRunCompletionSchema:
        if self.status not in {
            OcrPipelineRunStatus.SUCCEEDED,
            OcrPipelineRunStatus.PARTIAL_FAILED,
            OcrPipelineRunStatus.FAILED,
        }:
            raise ValueError("Completion status must be terminal.")
        if any(
            step.status in {OcrPipelineRunStepStatus.PENDING, OcrPipelineRunStepStatus.RUNNING}
            for step in self.steps
        ):
            raise ValueError("Completion requires terminal step statuses.")
        if self.status is not OcrPipelineRunStatus.FAILED and not self.steps:
            raise ValueError("A non-failed completion requires at least one step.")
        if self.status is OcrPipelineRunStatus.FAILED:
            if self.error is None:
                raise ValueError("A failed completion requires a safe error.")
            if self.result is not None:
                raise ValueError("A failed completion cannot include a result.")
        elif self.result is None:
            raise ValueError("A successful completion requires a bounded result.")
        elif self.error is not None:
            raise ValueError("A successful completion cannot include a run error.")
        return self
