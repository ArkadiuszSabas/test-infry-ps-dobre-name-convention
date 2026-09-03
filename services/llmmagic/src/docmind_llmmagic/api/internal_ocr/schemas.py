"""HTTP schemas for internal OCR pipeline endpoints."""

import re
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    field_validator,
)

from docmind_llmmagic.domain.pipeline.catalog import (
    SAFE_PIPELINE_IDENTIFIER_MAX_LENGTH,
    SAFE_PIPELINE_IDENTIFIER_PATTERN,
)

BlockStatusSchema = Literal["available", "disabled", "planned", "deprecated"]
DiagnosticSeveritySchema = Literal["error", "warning"]
FailurePolicySchema = Literal["required", "optional"]
PipelineRunStatusSchema = Literal["succeeded", "partial_failed", "failed"]
PipelineRunAcceptanceStatusSchema = Literal["accepted"]
PipelineRunStepStatusSchema = Literal["pending", "running", "succeeded", "failed", "skipped"]
PipelineRunMetricValueSchema = StrictBool | StrictInt | StrictFloat
PipelineRunActorTypeSchema = Literal["human", "connector", "system"]
PipelineRunAcquisitionReasonSchema = Literal["new", "retry", "expired_lease_takeover"]
SAFE_RUN_METADATA_KEY_PATTERN = r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$"
_SAFE_RUN_METADATA_KEY_RE = re.compile(SAFE_RUN_METADATA_KEY_PATTERN)
SAFE_DOCUMENT_REFERENCE_MAX_LENGTH = 2048
SAFE_DOCUMENT_REFERENCE_PATTERN = (
    r"^(?:azblob://[A-Za-z0-9](?:[A-Za-z0-9._~:/-]|%[0-9A-Fa-f]{2})*"
    r"|https://[A-Za-z0-9.-]+\.blob\.core\.windows\.net/"
    r"(?:[A-Za-z0-9._~:/-]|%[0-9A-Fa-f]{2})+)$"
)
SAFE_ERROR_CODE_PATTERN = r"^[A-Z][A-Z0-9_]{1,79}$"
SAFE_REASON_CODE_PATTERN = r"^[A-Z][A-Z0-9_]{1,79}$"
SAFE_ERROR_MESSAGE_MAX_LENGTH = 200
SAFE_DISPLAY_NAME_MAX_LENGTH = 120
SAFE_DISPLAY_NAME_PATTERN = r"^[^\x00-\x1F\x7F]+$"
SAFE_TRACE_VALUE_MAX_LENGTH = 320
MAX_CONTEXT_RESOLUTION_ATTRIBUTE_COUNT = 500
MAX_CONTEXT_RESOLUTION_SOURCE_COUNT = 16
MAX_CONTEXT_RESOLUTION_REASON_CODE_COUNT = 16
MAX_CONTEXT_RESOLUTION_TEXT_LENGTH = 1_000
MAX_CONTEXT_RESOLUTION_VALUE_LENGTH = 4_000


def _empty_int_list() -> list[int]:
    return []


class PipelineBlockSchema(BaseModel):
    """HTTP schema for one OCR pipeline block."""

    implementation_id: str
    step_type: str
    display_name: str
    description: str
    status: BlockStatusSchema
    category: str
    version: str
    requires: list[str]
    produces: list[str]
    default_config: dict[str, object]
    config_schema: dict[str, object]
    ui_hints: dict[str, object]
    allowed_failure_policies: list[FailurePolicySchema]


class PipelineBlockCatalogData(BaseModel):
    """HTTP data payload for the OCR block catalog."""

    catalog_version: str
    catalog_hash: str
    blocks: list[PipelineBlockSchema]


class PipelineBlockCatalogEnvelope(BaseModel):
    """Standard envelope for the OCR block catalog."""

    data: PipelineBlockCatalogData
    meta: dict[str, str] = Field(default_factory=dict)


class PipelineStepCompileRequest(BaseModel):
    """HTTP request schema for one proposed pipeline step."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(
        max_length=SAFE_PIPELINE_IDENTIFIER_MAX_LENGTH,
        pattern=SAFE_PIPELINE_IDENTIFIER_PATTERN,
    )
    implementation_id: str
    display_name: str | None = Field(
        default=None,
        max_length=SAFE_DISPLAY_NAME_MAX_LENGTH,
        pattern=SAFE_DISPLAY_NAME_PATTERN,
    )
    config: dict[str, object] = Field(default_factory=dict)
    failure_policy: FailurePolicySchema = "required"
    enabled: StrictBool = True


class PipelineDefinitionCompileRequest(BaseModel):
    """HTTP request schema for compiling a proposed pipeline definition."""

    model_config = ConfigDict(extra="forbid")

    pipeline_id: str = Field(
        max_length=SAFE_PIPELINE_IDENTIFIER_MAX_LENGTH,
        pattern=SAFE_PIPELINE_IDENTIFIER_PATTERN,
    )
    steps: list[PipelineStepCompileRequest]


class PipelineCompileDiagnosticSchema(BaseModel):
    """HTTP schema for one safe compile diagnostic."""

    severity: DiagnosticSeveritySchema
    code: str
    message: str
    step_id: str | None = None
    path: str | None = None


def _empty_compile_diagnostics() -> list[PipelineCompileDiagnosticSchema]:
    return []


class CompiledPipelineStepSchema(BaseModel):
    """HTTP schema for one compiled local pipeline step."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(
        max_length=SAFE_PIPELINE_IDENTIFIER_MAX_LENGTH,
        pattern=SAFE_PIPELINE_IDENTIFIER_PATTERN,
    )
    step_type: str = Field(
        max_length=SAFE_PIPELINE_IDENTIFIER_MAX_LENGTH,
        pattern=SAFE_PIPELINE_IDENTIFIER_PATTERN,
    )
    implementation_id: str = Field(
        max_length=SAFE_PIPELINE_IDENTIFIER_MAX_LENGTH,
        pattern=SAFE_PIPELINE_IDENTIFIER_PATTERN,
    )
    display_name: str = Field(
        max_length=SAFE_DISPLAY_NAME_MAX_LENGTH,
        pattern=SAFE_DISPLAY_NAME_PATTERN,
    )
    config: dict[str, object]
    failure_policy: FailurePolicySchema
    enabled: StrictBool


class CompiledPipelineDefinitionSchema(BaseModel):
    """HTTP schema for the compiled local pipeline definition."""

    model_config = ConfigDict(extra="forbid")

    pipeline_id: str = Field(
        max_length=SAFE_PIPELINE_IDENTIFIER_MAX_LENGTH,
        pattern=SAFE_PIPELINE_IDENTIFIER_PATTERN,
    )
    steps: list[CompiledPipelineStepSchema]


class PipelineDefinitionCompileData(BaseModel):
    """HTTP data payload for compile validation results."""

    valid: bool
    catalog_version: str
    catalog_hash: str
    diagnostics: list[PipelineCompileDiagnosticSchema]
    compiled_definition: CompiledPipelineDefinitionSchema | None = None


class PipelineDefinitionCompileEnvelope(BaseModel):
    """Standard envelope for compile validation results."""

    data: PipelineDefinitionCompileData
    meta: dict[str, str] = Field(default_factory=dict)


class PipelineRunTraceContextSchema(BaseModel):
    """Typed execution and business identifiers used only for observability."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(max_length=128, pattern=SAFE_PIPELINE_IDENTIFIER_PATTERN)
    attempt_id: str = Field(max_length=128, pattern=SAFE_PIPELINE_IDENTIFIER_PATTERN)
    attempt_number: StrictInt = Field(ge=1)
    fencing_token: StrictInt = Field(ge=1)
    acquisition_reason: PipelineRunAcquisitionReasonSchema
    actor_type: PipelineRunActorTypeSchema
    actor_internal_id: str | None = Field(default=None, max_length=SAFE_TRACE_VALUE_MAX_LENGTH)
    actor_login_missing: StrictBool = False
    document_source: str | None = Field(default=None, max_length=SAFE_TRACE_VALUE_MAX_LENGTH)
    document_connector: str | None = Field(default=None, max_length=SAFE_TRACE_VALUE_MAX_LENGTH)
    connector_instance_id: str | None = Field(default=None, max_length=SAFE_TRACE_VALUE_MAX_LENGTH)
    connector_display_name: str | None = Field(default=None, max_length=SAFE_TRACE_VALUE_MAX_LENGTH)
    connector_correlation_id: str | None = Field(
        default=None,
        max_length=SAFE_TRACE_VALUE_MAX_LENGTH,
    )
    correlation_id: str | None = Field(default=None, max_length=SAFE_TRACE_VALUE_MAX_LENGTH)


class PipelineRunRequest(BaseModel):
    """HTTP request schema for running a compiled OCR pipeline snapshot."""

    model_config = ConfigDict(extra="forbid")

    document_reference: str = Field(
        max_length=SAFE_DOCUMENT_REFERENCE_MAX_LENGTH,
        pattern=SAFE_DOCUMENT_REFERENCE_PATTERN,
    )
    run_id: str | None = Field(
        default=None,
        max_length=SAFE_PIPELINE_IDENTIFIER_MAX_LENGTH,
        pattern=SAFE_PIPELINE_IDENTIFIER_PATTERN,
    )
    user_id: str | None = Field(
        default=None,
        max_length=SAFE_TRACE_VALUE_MAX_LENGTH,
        pattern=SAFE_DISPLAY_NAME_PATTERN,
    )
    metadata: dict[str, PipelineRunMetricValueSchema] = Field(default_factory=dict)
    trace_context: PipelineRunTraceContextSchema | None = None
    compiled_definition: CompiledPipelineDefinitionSchema

    @field_validator("metadata")
    @classmethod
    def validate_metadata_keys(
        cls,
        value: dict[str, PipelineRunMetricValueSchema],
    ) -> dict[str, PipelineRunMetricValueSchema]:
        """Reject unsafe metadata keys without echoing the rejected key."""

        if any(_SAFE_RUN_METADATA_KEY_RE.fullmatch(key) is None for key in value):
            raise ValueError("Run metadata keys must be safe identifiers.")
        return value


class PipelineRunAcceptedData(BaseModel):
    """Safe response returned after an OCR run is admitted for execution."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    attempt_id: str
    status: PipelineRunAcceptanceStatusSchema


class PipelineRunAcceptedEnvelope(BaseModel):
    """Envelope for the asynchronous pipeline-run admission response."""

    data: PipelineRunAcceptedData
    meta: dict[str, str] = Field(default_factory=dict)


class PipelineRunErrorSchema(BaseModel):
    """HTTP schema for safe run error details."""

    code: str = Field(pattern=SAFE_ERROR_CODE_PATTERN)
    message: str = Field(
        max_length=SAFE_ERROR_MESSAGE_MAX_LENGTH,
        pattern=SAFE_DISPLAY_NAME_PATTERN,
    )


class PipelineRunTraceStepSchema(BaseModel):
    """HTTP schema for one safe pipeline run trace entry."""

    step_id: str
    step_type: str
    implementation_id: str
    status: PipelineRunStepStatusSchema
    duration_seconds: float = Field(ge=0)
    metrics: dict[str, PipelineRunMetricValueSchema]
    error: PipelineRunErrorSchema | None = None


class PipelineRunOcrPageResultSchema(BaseModel):
    """HTTP schema for one safe OCR result page."""

    page_number: int = Field(ge=1)
    status: str
    text: str
    text_truncated: bool
    lines: list[str]
    lines_truncated: bool
    confidence: float | None = None
    warning_codes: list[str]
    error_code: str | None = None
    fallback_used: bool
    fallback_reason_codes: list[str]
    primary_error_code: str | None = None


class PipelineRunOcrKeyValuePairSchema(BaseModel):
    """HTTP schema for one safe provider-detected key-value pair."""

    key: str
    value: str
    key_truncated: bool
    value_truncated: bool
    confidence: float | None = None
    page_number: int = Field(ge=1)
    bounding_polygon: list[float]
    order_index: int = Field(ge=1)
    source: str


class PipelineRunOcrResultSchema(BaseModel):
    """HTTP schema for safe OCR display results."""

    status: str
    provider_id: str
    model_id: str
    total_page_count: int = Field(ge=0)
    succeeded_page_count: int = Field(ge=0)
    failed_page_count: int = Field(ge=0)
    average_confidence: float | None = None
    low_confidence_page_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    pages_truncated: bool
    pages: list[PipelineRunOcrPageResultSchema]
    key_value_pairs_truncated: bool
    key_value_pairs: list[PipelineRunOcrKeyValuePairSchema]


class PipelineRunContextResolutionQualitySchema(BaseModel):
    """HTTP schema for safe Context Resolver quality metadata."""

    model_config = ConfigDict(extra="forbid")

    resolved_attribute_count: int = Field(ge=0)
    review_required_attribute_count: int = Field(ge=0)
    missing_required_attribute_count: int = Field(ge=0)
    missing_attribute_count: int = Field(ge=0)
    low_confidence_attribute_count: int = Field(ge=0)
    conflicting_attribute_count: int = Field(ge=0)


class PipelineRunContextResolutionSourceSchema(BaseModel):
    """HTTP schema for a safe Context Resolver source reference."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(max_length=64)
    order_index: int | None = Field(default=None, ge=0)
    page_number: int | None = Field(default=None, ge=1)
    line_number: int | None = Field(default=None, ge=1)
    key_value_index: int | None = Field(default=None, ge=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
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


class PipelineRunContextResolutionAttributeSchema(BaseModel):
    """HTTP schema for one safe Context Resolver attribute."""

    model_config = ConfigDict(extra="forbid")

    document_type_id: str | None = Field(default=None, max_length=128)
    attribute_external_id: str = Field(max_length=128)
    attribute_id: str | None = Field(default=None, max_length=128)
    display_name: str = Field(max_length=200)
    value_type: str | None = Field(default=None, max_length=64)
    required: StrictBool
    value: str | None = Field(default=None, max_length=MAX_CONTEXT_RESOLUTION_VALUE_LENGTH)
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    status: str = Field(max_length=64)
    requires_review: StrictBool
    sources: list[PipelineRunContextResolutionSourceSchema] = Field(
        max_length=MAX_CONTEXT_RESOLUTION_SOURCE_COUNT
    )
    reason_codes: list[Annotated[str, Field(max_length=80, pattern=SAFE_REASON_CODE_PATTERN)]] = (
        Field(max_length=MAX_CONTEXT_RESOLUTION_REASON_CODE_COUNT)
    )
    consistency_status: str | None = Field(default=None, max_length=32)
    compared_values: list[str] = Field(default_factory=list, max_length=16)
    compared_key_value_pages: list[int] = Field(
        default_factory=_empty_int_list,
        max_length=16,
    )
    compared_key_value_indexes: list[int] = Field(
        default_factory=_empty_int_list,
        max_length=16,
    )
    confidence_before: float | None = Field(default=None, ge=0, le=1)
    confidence_after: float | None = Field(default=None, ge=0, le=1)


class PipelineRunContextResolutionResultSchema(BaseModel):
    """HTTP schema for safe Context Resolver run output."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    status: PipelineRunStatusSchema
    document_type_id: str | None = Field(default=None, max_length=128)
    total_attribute_count: int = Field(ge=0)
    quality: PipelineRunContextResolutionQualitySchema
    attributes: list[PipelineRunContextResolutionAttributeSchema] = Field(
        max_length=MAX_CONTEXT_RESOLUTION_ATTRIBUTE_COUNT
    )


class PipelineRunData(BaseModel):
    """HTTP data payload for a completed internal pipeline run."""

    pipeline_id: str
    run_id: str
    status: PipelineRunStatusSchema
    trace: list[PipelineRunTraceStepSchema]
    metrics: dict[str, PipelineRunMetricValueSchema]
    diagnostics: list[PipelineCompileDiagnosticSchema] = Field(
        default_factory=_empty_compile_diagnostics
    )
    error: PipelineRunErrorSchema | None = None
    ocr_result: PipelineRunOcrResultSchema | None = None
    context_resolution_result: PipelineRunContextResolutionResultSchema | None = None


class PipelineRunEnvelope(BaseModel):
    """Standard envelope for internal OCR pipeline run results."""

    data: PipelineRunData
    meta: dict[str, str] = Field(default_factory=dict)
