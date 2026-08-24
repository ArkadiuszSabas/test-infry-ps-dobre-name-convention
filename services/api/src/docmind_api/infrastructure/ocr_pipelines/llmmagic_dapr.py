"""Dapr adapter for LLM Magic OCR pipeline catalog and compile validation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Literal, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from docmind_api.application.ocr_pipelines.errors import OcrPipelineLlmMagicUnavailableError
from docmind_api.domain.ocr_pipelines.models import (
    JsonObject,
    OcrPipelineBlockCatalog,
    OcrPipelineBlockMetadata,
    OcrPipelineBlockStatus,
    OcrPipelineDiagnostic,
    OcrPipelineDiagnosticSeverity,
    OcrPipelineDraftDefinition,
    OcrPipelineFailurePolicy,
    OcrPipelineValidationResult,
)
from docmind_backend_runtime import (
    DaprClientError,
    DaprHttpClient,
    DaprInvocationResponse,
    get_correlation_id,
)
from docmind_backend_runtime.correlation import CORRELATION_ID_HEADER

LLMMAGIC_DAPR_APP_ID = "docmind-llmmagic"
_CATALOG_METHOD = "internal/ocr/pipeline-blocks"
_COMPILE_METHOD = "internal/ocr/pipeline-definitions/compile"

_BlockStatus = Literal["available", "disabled", "planned", "deprecated"]
_FailurePolicy = Literal["required", "optional"]
_DiagnosticSeverity = Literal["error", "warning"]


class DaprLlmMagicOcrPipelineBlockCatalogClient:
    """Calls LLM Magic internal OCR pipeline endpoints through Dapr service invocation."""

    def __init__(
        self,
        *,
        dapr_client: DaprHttpClient,
        target_app_id: str = LLMMAGIC_DAPR_APP_ID,
    ) -> None:
        self._dapr_client = dapr_client
        self._target_app_id = target_app_id

    async def get_catalog(self) -> OcrPipelineBlockCatalog:
        """Return the authoritative OCR block catalog from LLM Magic."""

        try:
            response = await self._invoke_llmmagic(_CATALOG_METHOD)
            envelope = _parse_response_model(
                response,
                _PipelineBlockCatalogEnvelope,
                operation="catalog",
            )
        except _LlmMagicAdapterError as error:
            raise OcrPipelineLlmMagicUnavailableError(operation="catalog") from error

        return OcrPipelineBlockCatalog(
            catalog_version=envelope.data.catalog_version,
            catalog_hash=envelope.data.catalog_hash,
            blocks=tuple(_block_metadata(block) for block in envelope.data.blocks),
        )

    async def compile_definition(
        self,
        pipeline_id: UUID,
        definition: OcrPipelineDraftDefinition,
    ) -> OcrPipelineValidationResult:
        """Return LLM Magic technical compile diagnostics for a proposed definition."""

        try:
            response = await self._invoke_llmmagic(
                _COMPILE_METHOD,
                http_method="POST",
                json_body=_compile_request_payload(pipeline_id, definition),
            )
            envelope = _parse_response_model(
                response,
                _PipelineDefinitionCompileEnvelope,
                operation="compile",
            )
        except _LlmMagicAdapterError:
            return _compile_unavailable_result()

        return _validation_result(envelope.data)

    async def _invoke_llmmagic(
        self,
        method_name: str,
        *,
        http_method: str = "GET",
        json_body: object | None = None,
    ) -> DaprInvocationResponse:
        try:
            response = await self._dapr_client.invoke_method(
                self._target_app_id,
                method_name,
                http_method=http_method,
                headers=_correlation_headers(),
                json_body=json_body,
            )
        except DaprClientError as error:
            raise _LlmMagicAdapterError from error

        if response.status_code < 200 or response.status_code >= 300:
            raise _LlmMagicAdapterError
        return response


class _LlmMagicAdapterError(RuntimeError):
    """Private marker for unsafe or unavailable LLM Magic adapter responses."""


class _PipelineBlockSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    implementation_id: str
    step_type: str
    display_name: str
    description: str | None = None
    status: _BlockStatus
    category: str
    version: str
    requires: list[str] = Field(default_factory=list)
    produces: list[str] = Field(default_factory=list)
    default_config: dict[str, object] = Field(default_factory=dict)
    config_schema: dict[str, object] = Field(default_factory=dict)
    ui_hints: dict[str, object] = Field(default_factory=dict)
    allowed_failure_policies: list[_FailurePolicy]
    disabled_reason: str | None = None


class _PipelineBlockCatalogData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_version: str
    catalog_hash: str
    blocks: list[_PipelineBlockSchema]


class _PipelineBlockCatalogEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: _PipelineBlockCatalogData
    meta: dict[str, str] = Field(default_factory=dict)


class _PipelineCompileDiagnosticSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: _DiagnosticSeverity
    code: str
    message: str
    step_id: str | None = None
    path: str | None = None


class _CompiledPipelineStepSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    step_type: str
    implementation_id: str
    display_name: str
    config: dict[str, object]
    failure_policy: _FailurePolicy
    enabled: bool


class _CompiledPipelineDefinitionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_id: str
    steps: list[_CompiledPipelineStepSchema]


class _PipelineDefinitionCompileData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    catalog_version: str
    catalog_hash: str
    diagnostics: list[_PipelineCompileDiagnosticSchema]
    compiled_definition: _CompiledPipelineDefinitionSchema | None = None


class _PipelineDefinitionCompileEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: _PipelineDefinitionCompileData
    meta: dict[str, str] = Field(default_factory=dict)


def _parse_response_model[ModelT: BaseModel](
    response: DaprInvocationResponse,
    model_type: type[ModelT],
    *,
    operation: str,
) -> ModelT:
    try:
        payload = response.json()
        return model_type.model_validate(payload)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as error:
        raise _LlmMagicAdapterError(f"Invalid LLM Magic {operation} response.") from error


def _block_metadata(block: _PipelineBlockSchema) -> OcrPipelineBlockMetadata:
    return OcrPipelineBlockMetadata(
        implementation_id=block.implementation_id,
        step_type=block.step_type,
        display_name=block.display_name,
        description=block.description,
        status=OcrPipelineBlockStatus(block.status),
        category=block.category,
        version=block.version,
        requires=tuple(block.requires),
        produces=tuple(block.produces),
        default_config=cast(JsonObject, block.default_config),
        config_schema=cast(JsonObject, block.config_schema),
        ui_hints=cast(JsonObject, block.ui_hints),
        allowed_failure_policies=tuple(
            OcrPipelineFailurePolicy(failure_policy)
            for failure_policy in block.allowed_failure_policies
        ),
        disabled_reason=block.disabled_reason,
    )


def _compile_request_payload(
    pipeline_id: UUID,
    definition: OcrPipelineDraftDefinition,
) -> Mapping[str, object]:
    return {
        "pipeline_id": str(pipeline_id),
        "steps": [
            {
                "step_id": step.step_id,
                "implementation_id": step.implementation_id,
                "display_name": step.display_name,
                "config": dict(step.config),
                "failure_policy": step.failure_policy.value,
                "enabled": step.enabled,
            }
            for step in definition.steps
        ],
    }


def _validation_result(data: _PipelineDefinitionCompileData) -> OcrPipelineValidationResult:
    compiled_snapshot = None
    if data.valid and data.compiled_definition is not None:
        compiled_snapshot = cast(JsonObject, data.compiled_definition.model_dump(mode="json"))
    diagnostics = tuple(_diagnostic(diagnostic) for diagnostic in data.diagnostics)
    if not data.valid and not any(diagnostic.is_error for diagnostic in diagnostics):
        diagnostics = (
            *diagnostics,
            OcrPipelineDiagnostic(
                severity=OcrPipelineDiagnosticSeverity.ERROR,
                code="LLMMAGIC_COMPILE_INVALID",
                message="LLM Magic reported the OCR pipeline definition as technically invalid.",
            ),
        )

    return OcrPipelineValidationResult(
        diagnostics=diagnostics,
        compiled_snapshot=compiled_snapshot,
        catalog_version=data.catalog_version,
        catalog_hash=data.catalog_hash,
    )


def _diagnostic(diagnostic: _PipelineCompileDiagnosticSchema) -> OcrPipelineDiagnostic:
    return OcrPipelineDiagnostic(
        severity=OcrPipelineDiagnosticSeverity(diagnostic.severity),
        code=diagnostic.code,
        message=diagnostic.message,
        step_id=diagnostic.step_id,
        path=diagnostic.path,
    )


def _compile_unavailable_result() -> OcrPipelineValidationResult:
    return OcrPipelineValidationResult(
        diagnostics=(
            OcrPipelineDiagnostic(
                severity=OcrPipelineDiagnosticSeverity.ERROR,
                code="LLMMAGIC_COMPILE_UNAVAILABLE",
                message="LLM Magic compile validation is unavailable.",
            ),
        ),
    )


def _correlation_headers() -> Mapping[str, str]:
    correlation_id = get_correlation_id()
    if correlation_id is None:
        return {}
    return {CORRELATION_ID_HEADER: correlation_id}
