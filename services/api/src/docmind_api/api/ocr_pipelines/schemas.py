"""HTTP schemas for OCR pipeline admin endpoints."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from docmind_api.domain.ocr_pipelines.models import (
    OCR_PIPELINE_DESCRIPTION_MAX_LENGTH,
    OCR_PIPELINE_DISPLAY_NAME_MAX_LENGTH,
    OCR_PIPELINE_IMPLEMENTATION_ID_MAX_LENGTH,
    OCR_PIPELINE_NAME_MAX_LENGTH,
    OCR_PIPELINE_STEP_ID_MAX_LENGTH,
    OcrPipelineBlockStatus,
    OcrPipelineDiagnosticSeverity,
    OcrPipelineFailurePolicy,
    OcrPipelineKind,
    OcrPipelineLifecycle,
)


class OcrPipelineStepRequest(BaseModel):
    """HTTP request schema for one OCR pipeline builder step."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(max_length=OCR_PIPELINE_STEP_ID_MAX_LENGTH)
    implementation_id: str = Field(max_length=OCR_PIPELINE_IMPLEMENTATION_ID_MAX_LENGTH)
    display_name: str = Field(max_length=OCR_PIPELINE_DISPLAY_NAME_MAX_LENGTH)
    enabled: bool = True
    failure_policy: OcrPipelineFailurePolicy = OcrPipelineFailurePolicy.REQUIRED
    config: dict[str, object] = Field(default_factory=dict)


def _empty_step_requests() -> list[OcrPipelineStepRequest]:
    return []


class CreateOcrPipelineRequest(BaseModel):
    """HTTP request schema for creating an OCR pipeline draft."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=OCR_PIPELINE_NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=OCR_PIPELINE_DESCRIPTION_MAX_LENGTH)
    schema_version: int = 1
    kind: OcrPipelineKind = OcrPipelineKind.LINEAR
    steps: list[OcrPipelineStepRequest] = Field(default_factory=_empty_step_requests)

    @model_validator(mode="after")
    def require_phase_one_contract(self) -> Self:
        """Keep the phase 1 admin contract stable."""

        if self.schema_version != 1:
            raise ValueError("OCR pipeline schema_version must be 1.")
        if self.kind != OcrPipelineKind.LINEAR:
            raise ValueError("OCR pipeline kind must be linear.")
        return self


class UpdateOcrPipelineDraftRequest(BaseModel):
    """HTTP request schema for editing an OCR pipeline draft."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=OCR_PIPELINE_NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=OCR_PIPELINE_DESCRIPTION_MAX_LENGTH)
    schema_version: int | None = None
    kind: OcrPipelineKind | None = None
    steps: list[OcrPipelineStepRequest] | None = None

    @model_validator(mode="after")
    def reject_invalid_patch_values(self) -> Self:
        """Reject explicit nulls and non-phase-1 contract values."""

        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("OCR pipeline name cannot be null.")
        if "steps" in self.model_fields_set and self.steps is None:
            raise ValueError("OCR pipeline steps cannot be null.")
        if "schema_version" in self.model_fields_set and self.schema_version != 1:
            raise ValueError("OCR pipeline schema_version must be 1.")
        if "kind" in self.model_fields_set and self.kind != OcrPipelineKind.LINEAR:
            raise ValueError("OCR pipeline kind must be linear.")
        return self


class OcrPipelineStepSchema(BaseModel):
    """HTTP schema for one OCR pipeline step."""

    step_id: str
    implementation_id: str
    display_name: str
    enabled: bool
    failure_policy: OcrPipelineFailurePolicy
    config: dict[str, object]


class OcrPipelineDefinitionSchema(BaseModel):
    """HTTP schema for a draft or published OCR pipeline definition."""

    schema_version: int
    kind: OcrPipelineKind
    name: str
    description: str | None
    steps: list[OcrPipelineStepSchema]


class OcrPipelineDiagnosticSchema(BaseModel):
    """HTTP schema for one validation diagnostic."""

    severity: OcrPipelineDiagnosticSeverity
    code: str
    path: str | None
    step_id: str | None
    message: str


class OcrPipelineValidationSchema(BaseModel):
    """HTTP schema for OCR pipeline validation results."""

    valid: bool
    diagnostics: list[OcrPipelineDiagnosticSchema]
    catalog_version: str | None
    catalog_hash: str | None
    compiled_snapshot: dict[str, object] | None = None


class OcrPipelineSummarySchema(BaseModel):
    """HTTP schema for OCR pipeline list rows."""

    id: UUID
    name: str
    description: str | None
    lifecycle: OcrPipelineLifecycle
    is_default: bool
    has_draft: bool
    published_version: int | None
    last_validation_valid: bool | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    archived_at: datetime | None


class OcrPipelineDetailSchema(BaseModel):
    """HTTP schema for one OCR pipeline definition."""

    id: UUID
    lifecycle: OcrPipelineLifecycle
    is_default: bool
    draft: OcrPipelineDefinitionSchema | None
    published_definition: OcrPipelineDefinitionSchema | None
    published_version: int | None
    last_validation: OcrPipelineValidationSchema | None
    compiled_snapshot: dict[str, object] | None
    catalog_version: str | None
    catalog_hash: str | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    archived_at: datetime | None


class OcrPipelineEnvelope(BaseModel):
    """Standard API response envelope for one OCR pipeline."""

    data: OcrPipelineDetailSchema
    meta: dict[str, str] = Field(default_factory=dict)


class OcrPipelineListSchema(BaseModel):
    """HTTP schema for OCR pipeline list results."""

    pipelines: list[OcrPipelineSummarySchema]


class OcrPipelineListMeta(BaseModel):
    """HTTP metadata for OCR pipeline lists."""

    total_count: int


class OcrPipelineListEnvelope(BaseModel):
    """Standard API response envelope for OCR pipeline lists."""

    data: OcrPipelineListSchema
    meta: OcrPipelineListMeta


class OcrPipelineValidationEnvelope(BaseModel):
    """Standard API response envelope for validation results."""

    data: OcrPipelineValidationSchema
    meta: dict[str, str] = Field(default_factory=dict)


class DeleteOcrPipelineSchema(BaseModel):
    """HTTP schema for a deleted OCR pipeline draft."""

    id: UUID
    deleted: bool


class DeleteOcrPipelineEnvelope(BaseModel):
    """Standard API response envelope for OCR pipeline deletion."""

    data: DeleteOcrPipelineSchema
    meta: dict[str, str] = Field(default_factory=dict)


class OcrPipelineBlockSchema(BaseModel):
    """HTTP schema for one OCR pipeline block catalog entry."""

    implementation_id: str
    step_type: str
    display_name: str
    description: str | None
    status: OcrPipelineBlockStatus
    category: str
    version: str
    requires: list[str]
    produces: list[str]
    default_config: dict[str, object]
    config_schema: dict[str, object]
    ui_hints: dict[str, object]
    allowed_failure_policies: list[OcrPipelineFailurePolicy]
    disabled_reason: str | None


class OcrPipelineBlockCatalogSchema(BaseModel):
    """HTTP schema for the OCR pipeline block catalog."""

    catalog_version: str
    catalog_hash: str
    blocks: list[OcrPipelineBlockSchema]


class OcrPipelineBlockCatalogEnvelope(BaseModel):
    """Standard API response envelope for the OCR pipeline block catalog."""

    data: OcrPipelineBlockCatalogSchema
    meta: dict[str, str] = Field(default_factory=dict)
