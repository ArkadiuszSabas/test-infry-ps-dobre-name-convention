"""Dapr adapter for LLM Magic OCR pipeline direct run invocation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from docmind_api.application.ocr_pipeline_runs.errors import (
    OcrPipelineRunInvocationIndeterminateError,
)
from docmind_api.application.ocr_pipeline_runs.ports import OcrPipelineRunInvocationContext
from docmind_api.domain.ocr_pipeline_runs.models import (
    MetricValue,
    OcrPipelineRunActorType,
    OcrPipelineRunDiagnostic,
    OcrPipelineRunDiagnosticSeverity,
    OcrPipelineRunError,
    OcrPipelineRunRecord,
    OcrPipelineRunStatus,
    OcrPipelineRunStep,
    OcrPipelineRunStepStatus,
)
from docmind_backend_runtime import (
    DaprClientError,
    DaprClientTimeoutError,
    DaprHttpClient,
    DaprInvocationResponse,
    get_correlation_id,
)
from docmind_backend_runtime.correlation import CORRELATION_ID_HEADER

LLMMAGIC_DAPR_APP_ID = "docmind-llmmagic"
_RUN_METHOD = "internal/ocr/pipeline-runs"

_RunStatus = Literal["succeeded", "partial_failed", "failed"]
_StepStatus = Literal["pending", "running", "succeeded", "failed", "skipped"]
_DiagnosticSeverity = Literal["error", "warning"]
_MetricValue = StrictBool | StrictInt | StrictFloat
MAX_RESULT_PAGE_COUNT = 50
MAX_RESULT_TEXT_LENGTH = 200_000
MAX_PAGE_TEXT_LENGTH = 20_000
MAX_PAGE_LINE_COUNT = 250
MAX_LINE_TEXT_LENGTH = 1_000
MAX_KEY_VALUE_PAIR_COUNT = 2_000
MAX_KEY_VALUE_TEXT_LENGTH = 1_000
MAX_CONTEXT_RESOLUTION_ATTRIBUTE_COUNT = 500
MAX_CONTEXT_RESOLUTION_SOURCE_COUNT = 16
MAX_CONTEXT_RESOLUTION_REASON_CODE_COUNT = 16
MAX_CONTEXT_RESOLUTION_COMPARISON_COUNT = 16
MAX_CONTEXT_RESOLUTION_VALUE_LENGTH = 4_000
SAFE_CONTEXT_RESOLUTION_REASON_CODE_PATTERN = r"^[A-Z][A-Z0-9_]{1,79}$"
_CONFLICTING_CONSISTENCY_REASON_CODES = frozenset({"CONFLICTING_VALUES", "KV_CONSISTENCY_CONFLICT"})


def _empty_int_list() -> list[int]:
    return []


class DaprLlmMagicOcrPipelineRunInvoker:
    """Calls LLM Magic internal OCR pipeline run endpoint through Dapr."""

    def __init__(
        self,
        *,
        dapr_client: DaprHttpClient,
        target_app_id: str = LLMMAGIC_DAPR_APP_ID,
    ) -> None:
        self._dapr_client = dapr_client
        self._target_app_id = target_app_id

    async def invoke_run(
        self,
        record: OcrPipelineRunRecord,
        context: OcrPipelineRunInvocationContext | None = None,
    ) -> OcrPipelineRunRecord:
        """Invoke LLM Magic and map its safe run output to an API-owned record."""

        try:
            correlation_id = get_correlation_id()
            response = await self._dapr_client.invoke_method(
                self._target_app_id,
                _RUN_METHOD,
                http_method="POST",
                headers=_correlation_headers(correlation_id),
                json_body=_run_request_payload(
                    record,
                    context=context,
                    correlation_id=correlation_id,
                ),
            )
        except DaprClientTimeoutError as error:
            raise OcrPipelineRunInvocationIndeterminateError() from error
        except DaprClientError as error:
            raise OcrPipelineRunInvocationIndeterminateError() from error

        if response.status_code < 200 or response.status_code >= 300:
            raise OcrPipelineRunInvocationIndeterminateError()

        try:
            envelope = _parse_response_model(response, _PipelineRunEnvelope)
            _validate_response_identity(record, envelope.data)
            return _record_from_run_data(record, envelope.data)
        except Exception as error:
            raise OcrPipelineRunInvocationIndeterminateError() from error


class _LlmMagicRunAdapterError(RuntimeError):
    """Private marker for unsafe or unavailable LLM Magic run responses."""


class _PipelineCompileDiagnosticSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: _DiagnosticSeverity
    code: str
    message: str
    step_id: str | None = None
    path: str | None = None


class _PipelineRunErrorSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class _PipelineRunTraceStepSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    step_type: str
    implementation_id: str
    status: _StepStatus
    duration_seconds: float = Field(ge=0)
    metrics: dict[str, _MetricValue]
    error: _PipelineRunErrorSchema | None = None


class _PipelineRunOcrPageResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    status: str
    text: str = Field(max_length=MAX_PAGE_TEXT_LENGTH)
    text_truncated: bool
    lines: list[Annotated[str, Field(max_length=MAX_LINE_TEXT_LENGTH)]] = Field(
        max_length=MAX_PAGE_LINE_COUNT
    )
    lines_truncated: bool
    confidence: float | None = None
    warning_codes: list[str]
    error_code: str | None = None
    fallback_used: bool
    fallback_reason_codes: list[str]
    primary_error_code: str | None = None


class _PipelineRunOcrKeyValuePairSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(max_length=MAX_KEY_VALUE_TEXT_LENGTH)
    value: str = Field(max_length=MAX_KEY_VALUE_TEXT_LENGTH)
    key_truncated: bool
    value_truncated: bool
    confidence: float | None = None
    page_number: int = Field(ge=1)
    bounding_polygon: list[float]
    order_index: int = Field(ge=1)
    source: str


class _PipelineRunOcrResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    pages: list[_PipelineRunOcrPageResultSchema] = Field(max_length=MAX_RESULT_PAGE_COUNT)
    key_value_pairs_truncated: bool = False
    key_value_pairs: list[_PipelineRunOcrKeyValuePairSchema] = Field(
        default_factory=list[_PipelineRunOcrKeyValuePairSchema],
        max_length=MAX_KEY_VALUE_PAIR_COUNT,
    )

    @model_validator(mode="after")
    def validate_text_budget(self) -> _PipelineRunOcrResultSchema:
        if sum(_page_text_length(page) for page in self.pages) > MAX_RESULT_TEXT_LENGTH:
            raise ValueError("OCR result text payload exceeds the safe display budget.")
        return self


def _page_text_length(page: _PipelineRunOcrPageResultSchema) -> int:
    return len(page.text) + sum(len(line) for line in page.lines)


class _PipelineRunContextResolutionQualitySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolved_attribute_count: int = Field(ge=0)
    review_required_attribute_count: int = Field(ge=0)
    missing_required_attribute_count: int = Field(ge=0)
    missing_attribute_count: int = Field(ge=0)
    low_confidence_attribute_count: int = Field(ge=0)
    conflicting_attribute_count: int = Field(ge=0)


class _PipelineRunContextResolutionSourceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(max_length=64)
    page_number: int | None = Field(default=None, ge=1)
    line_number: int | None = Field(default=None, ge=1)
    key_value_index: int | None = Field(default=None, ge=1)
    confidence: float | None = Field(default=None, ge=0, le=1)


class _PipelineRunContextResolutionAttributeSchema(BaseModel):
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
    sources: list[_PipelineRunContextResolutionSourceSchema] = Field(
        max_length=MAX_CONTEXT_RESOLUTION_SOURCE_COUNT
    )
    reason_codes: list[
        Annotated[str, Field(max_length=80, pattern=SAFE_CONTEXT_RESOLUTION_REASON_CODE_PATTERN)]
    ] = Field(max_length=MAX_CONTEXT_RESOLUTION_REASON_CODE_COUNT)
    consistency_status: str | None = Field(default=None, max_length=32)
    compared_values: list[Annotated[str, Field(max_length=MAX_CONTEXT_RESOLUTION_VALUE_LENGTH)]] = (
        Field(default_factory=list, max_length=MAX_CONTEXT_RESOLUTION_COMPARISON_COUNT)
    )
    compared_key_value_pages: list[StrictInt] = Field(
        default_factory=_empty_int_list,
        max_length=MAX_CONTEXT_RESOLUTION_COMPARISON_COUNT,
    )
    compared_key_value_indexes: list[StrictInt] = Field(
        default_factory=_empty_int_list,
        max_length=MAX_CONTEXT_RESOLUTION_COMPARISON_COUNT,
    )
    confidence_before: float | None = Field(default=None, ge=0, le=1)
    confidence_after: float | None = Field(default=None, ge=0, le=1)

    @field_validator("compared_key_value_pages", "compared_key_value_indexes")
    @classmethod
    def validate_positive_key_value_references(cls, values: list[int]) -> list[int]:
        if any(value < 1 for value in values):
            raise ValueError("Compared key-value references must be positive integers.")
        return values

    @model_validator(mode="after")
    def validate_consistency_comparison_lengths(
        self,
    ) -> _PipelineRunContextResolutionAttributeSchema:
        """Reject payloads that cannot describe every verifier comparison safely."""

        comparison_fields = {
            "compared_values",
            "compared_key_value_pages",
            "compared_key_value_indexes",
        }
        if self.consistency_status is not None and not comparison_fields <= self.model_fields_set:
            raise ValueError("Verifier consistency status requires every comparison field.")
        if (
            self.consistency_status == "conflicting"
            and not _CONFLICTING_CONSISTENCY_REASON_CODES.intersection(self.reason_codes)
        ):
            raise ValueError("Conflicting verifier results must include a conflict reason code.")
        compared_lengths = {
            len(self.compared_values),
            len(self.compared_key_value_pages),
            len(self.compared_key_value_indexes),
        }
        if len(compared_lengths) != 1:
            raise ValueError("Compared verifier values and locations must have equal lengths.")
        return self


class _PipelineRunContextResolutionResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    status: _RunStatus
    document_type_id: str | None = Field(default=None, max_length=128)
    total_attribute_count: int = Field(ge=0)
    quality: _PipelineRunContextResolutionQualitySchema
    attributes: list[_PipelineRunContextResolutionAttributeSchema] = Field(
        max_length=MAX_CONTEXT_RESOLUTION_ATTRIBUTE_COUNT
    )


class _PipelineRunData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_id: str
    run_id: str
    status: _RunStatus
    trace: list[_PipelineRunTraceStepSchema]
    metrics: dict[str, _MetricValue]
    diagnostics: list[_PipelineCompileDiagnosticSchema]
    error: _PipelineRunErrorSchema | None = None
    ocr_result: _PipelineRunOcrResultSchema | None = None
    context_resolution_result: _PipelineRunContextResolutionResultSchema | None = None


class _PipelineRunEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: _PipelineRunData
    meta: dict[str, str] = Field(default_factory=dict)


def _parse_response_model[ModelT: BaseModel](
    response: DaprInvocationResponse,
    model_type: type[ModelT],
) -> ModelT:
    try:
        payload = response.json()
        return model_type.model_validate(payload)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as error:
        raise _LlmMagicRunAdapterError("Invalid LLM Magic run response.") from error


def _run_request_payload(
    record: OcrPipelineRunRecord,
    *,
    context: OcrPipelineRunInvocationContext | None,
    correlation_id: str | None,
) -> Mapping[str, object]:
    metadata: dict[str, MetricValue] = {
        "direct_path": True,
        "pipeline_version": record.pipeline_version,
    }
    document_size_bytes = record.metrics.get("document_size_bytes")
    if isinstance(document_size_bytes, int) and not isinstance(document_size_bytes, bool):
        metadata["document_size_bytes"] = document_size_bytes

    payload: dict[str, object] = {
        "document_reference": record.document_reference,
        "run_id": str(record.id),
        "metadata": metadata,
        "compiled_definition": dict(record.compiled_snapshot),
    }
    if context is not None:
        payload["trace_context"] = {
            "document_id": str(record.document_id),
            "attempt_id": str(context.attempt_id),
            "attempt_number": context.attempt_number,
            "fencing_token": context.fencing_token,
            "acquisition_reason": context.acquisition_reason.value,
            "actor_type": record.started_by_actor_type.value,
            "actor_internal_id": record.started_by_actor_id,
            "actor_login_missing": (
                record.started_by_actor_type == OcrPipelineRunActorType.HUMAN
                and record.started_by_actor_login is None
            ),
            "document_source": record.document_source,
            "document_connector": record.document_connector,
            "connector_instance_id": record.connector_instance_id,
            "connector_display_name": record.connector_display_name,
            "connector_correlation_id": record.connector_correlation_id,
            "correlation_id": correlation_id,
        }
    user_id = _trace_user_id(record)
    if user_id is not None:
        payload["user_id"] = user_id
    return payload


def _trace_user_id(record: OcrPipelineRunRecord) -> str | None:
    if record.started_by_actor_type == OcrPipelineRunActorType.HUMAN:
        return record.started_by_actor_login
    if record.started_by_actor_type == OcrPipelineRunActorType.CONNECTOR:
        return record.started_by_actor_id
    return None


def _validate_response_identity(
    record: OcrPipelineRunRecord,
    data: _PipelineRunData,
) -> None:
    if data.run_id != str(record.id) or data.pipeline_id != str(record.pipeline_id):
        raise _LlmMagicRunAdapterError("LLM Magic run response identity mismatch.")


def _record_from_run_data(
    record: OcrPipelineRunRecord,
    data: _PipelineRunData,
) -> OcrPipelineRunRecord:
    steps_by_id = {step.step_id: step for step in record.steps}
    trace_steps = tuple(_step_from_trace(step, steps_by_id) for step in data.trace)
    steps = trace_steps if trace_steps else record.steps
    status = OcrPipelineRunStatus(data.status)
    completed_at = record.started_at or record.updated_at
    return replace(
        record,
        status=status,
        steps=steps,
        metrics={
            **{
                key: value
                for key, value in data.metrics.items()
                if not key.startswith("execution_")
            },
            **{key: value for key, value in record.metrics.items() if key.startswith("execution_")},
        },
        diagnostics=tuple(_diagnostic(diagnostic) for diagnostic in data.diagnostics),
        error=_error(data.error),
        result_payload=_result_payload_for_status(
            status,
            data.ocr_result,
            data.context_resolution_result,
        ),
        completed_at=completed_at,
        updated_at=completed_at,
    )


def _step_from_trace(
    step: _PipelineRunTraceStepSchema,
    steps_by_id: Mapping[str, OcrPipelineRunStep],
) -> OcrPipelineRunStep:
    existing = steps_by_id.get(step.step_id)
    display_name = existing.display_name if existing is not None else step.step_id
    return OcrPipelineRunStep(
        step_id=step.step_id,
        step_type=step.step_type,
        implementation_id=step.implementation_id,
        display_name=display_name,
        status=OcrPipelineRunStepStatus(step.status),
        duration_seconds=step.duration_seconds,
        metrics={key: value for key, value in step.metrics.items()},
        error=_error(step.error),
    )


def _result_payload_for_status(
    status: OcrPipelineRunStatus,
    ocr_result: _PipelineRunOcrResultSchema | None,
    context_resolution_result: _PipelineRunContextResolutionResultSchema | None,
) -> dict[str, object] | None:
    if status not in {OcrPipelineRunStatus.SUCCEEDED, OcrPipelineRunStatus.PARTIAL_FAILED}:
        return None
    return _result_payload(ocr_result, context_resolution_result)


def _result_payload(
    ocr_result: _PipelineRunOcrResultSchema | None,
    context_resolution_result: _PipelineRunContextResolutionResultSchema | None,
) -> dict[str, object] | None:
    if ocr_result is None:
        return None

    payload: dict[str, object] = {
        str(key): value for key, value in ocr_result.model_dump(mode="json").items()
    }
    if context_resolution_result is not None:
        payload["context_resolution_result"] = context_resolution_result.model_dump(mode="json")

    return payload


def _diagnostic(diagnostic: _PipelineCompileDiagnosticSchema) -> OcrPipelineRunDiagnostic:
    return OcrPipelineRunDiagnostic(
        severity=OcrPipelineRunDiagnosticSeverity(diagnostic.severity),
        code=diagnostic.code,
        message=diagnostic.message,
        step_id=diagnostic.step_id,
        path=diagnostic.path,
    )


def _error(error: _PipelineRunErrorSchema | None) -> OcrPipelineRunError | None:
    if error is None:
        return None
    return OcrPipelineRunError(code=error.code, message=error.message)


def _correlation_headers(correlation_id: str | None) -> Mapping[str, str]:
    if correlation_id is None:
        return {}
    return {CORRELATION_ID_HEADER: correlation_id}
