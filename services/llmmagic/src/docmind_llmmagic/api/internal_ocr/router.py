"""Internal OCR pipeline endpoints for the DocMind.ai LLM Magic service."""

from collections.abc import Callable
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends

from docmind_backend_runtime import get_correlation_id
from docmind_llmmagic.api.internal_ocr.schemas import (
    CompiledPipelineDefinitionSchema,
    CompiledPipelineStepSchema,
    PipelineBlockCatalogData,
    PipelineBlockCatalogEnvelope,
    PipelineBlockSchema,
    PipelineCompileDiagnosticSchema,
    PipelineDefinitionCompileData,
    PipelineDefinitionCompileEnvelope,
    PipelineDefinitionCompileRequest,
    PipelineRunContextResolutionAttributeSchema,
    PipelineRunContextResolutionQualitySchema,
    PipelineRunContextResolutionResultSchema,
    PipelineRunContextResolutionSourceSchema,
    PipelineRunData,
    PipelineRunEnvelope,
    PipelineRunErrorSchema,
    PipelineRunOcrKeyValuePairSchema,
    PipelineRunOcrPageResultSchema,
    PipelineRunOcrResultSchema,
    PipelineRunRequest,
    PipelineRunStatusSchema,
    PipelineRunTraceStepSchema,
)
from docmind_llmmagic.application.pipeline.compiler import PipelineDefinitionCompiler
from docmind_llmmagic.application.pipeline.invocation.context_resolution_result import (
    PipelineInvocationContextResolutionAttribute,
    PipelineInvocationContextResolutionQuality,
    PipelineInvocationContextResolutionResult,
    PipelineInvocationContextResolutionSource,
)
from docmind_llmmagic.application.pipeline.invocation.contracts import PipelineTraceContext
from docmind_llmmagic.application.pipeline.invocation.ocr_result import (
    PipelineInvocationOcrKeyValuePair,
    PipelineInvocationOcrPageResult,
    PipelineInvocationOcrResult,
)
from docmind_llmmagic.application.pipeline.invocation.service import (
    PipelineInvocationCommand,
    PipelineInvocationResult,
    PipelineInvocationService,
)
from docmind_llmmagic.domain.pipeline.catalog import (
    PipelineBlockMetadata,
    PipelineCompileCommand,
    PipelineCompileDiagnostic,
    PipelineCompileResult,
    PipelineDiagnosticSeverity,
    PipelineStepCompileInput,
)
from docmind_llmmagic.domain.pipeline.models import (
    FailurePolicy,
    PipelineDefinition,
    PipelineStepDefinition,
    StepError,
    StepResult,
)

PipelineCompilerDependency = Callable[[], PipelineDefinitionCompiler]
PipelineInvocationDependency = Callable[..., PipelineInvocationService]
InternalOcrAccessDependency = Callable[[], None]


def create_denied_internal_ocr_router(
    *,
    access_dependency: InternalOcrAccessDependency,
) -> APIRouter:
    """Create fail-closed internal OCR routes without parsing request bodies."""

    router = APIRouter(
        prefix="/internal/ocr",
        tags=["internal-ocr"],
        dependencies=[Depends(access_dependency)],
    )

    async def deny_internal_ocr_access() -> None:
        return None

    router.add_api_route(
        "/pipeline-blocks",
        deny_internal_ocr_access,
        methods=["GET"],
    )
    router.add_api_route(
        "/pipeline-definitions/compile",
        deny_internal_ocr_access,
        methods=["POST"],
    )
    router.add_api_route(
        "/pipeline-runs",
        deny_internal_ocr_access,
        methods=["POST"],
    )
    return router


def create_internal_ocr_router(
    *,
    compiler_dependency: PipelineCompilerDependency,
    invocation_dependency: PipelineInvocationDependency,
    access_dependency: InternalOcrAccessDependency,
) -> APIRouter:
    """Create the internal OCR router with bootstrap-provided dependencies."""

    router = APIRouter(
        prefix="/internal/ocr",
        tags=["internal-ocr"],
        dependencies=[Depends(access_dependency)],
    )

    async def get_pipeline_blocks(
        compiler: Annotated[PipelineDefinitionCompiler, Depends(compiler_dependency)],
    ) -> PipelineBlockCatalogEnvelope:
        return PipelineBlockCatalogEnvelope(
            data=PipelineBlockCatalogData(
                catalog_version=compiler.catalog.version,
                catalog_hash=compiler.catalog.catalog_hash,
                blocks=[_block_schema(block) for block in compiler.catalog.metadata],
            )
        )

    async def compile_pipeline_definition(
        request: PipelineDefinitionCompileRequest,
        compiler: Annotated[PipelineDefinitionCompiler, Depends(compiler_dependency)],
    ) -> PipelineDefinitionCompileEnvelope:
        result = compiler.compile(_compile_command(request))
        return PipelineDefinitionCompileEnvelope(data=_compile_data(result))

    async def run_pipeline_definition(
        request: PipelineRunRequest,
        compiler: Annotated[PipelineDefinitionCompiler, Depends(compiler_dependency)],
        invocation_service: Annotated[PipelineInvocationService, Depends(invocation_dependency)],
    ) -> PipelineRunEnvelope:
        compile_result = compiler.compile(
            _compile_command_from_definition(request.compiled_definition)
        )
        compiled_definition = compile_result.compiled_definition
        if not compile_result.valid or compiled_definition is None:
            return PipelineRunEnvelope(
                data=_invalid_run_data(
                    request=request,
                    diagnostics=compile_result.diagnostics,
                )
            )

        if not _compiled_definition_matches_request(
            request.compiled_definition,
            compiled_definition,
        ):
            return PipelineRunEnvelope(
                data=_invalid_run_data(
                    request=request,
                    diagnostics=(
                        *compile_result.diagnostics,
                        _compiled_definition_mismatch_diagnostic(),
                    ),
                )
            )

        result = await invocation_service.invoke_compiled_definition(
            PipelineInvocationCommand(
                document_reference=request.document_reference,
                pipeline_id=compiled_definition.pipeline_id,
                run_id=request.run_id,
                user_id=request.user_id,
                session_id=get_correlation_id(),
                metadata=dict(request.metadata),
                trace_context=(
                    PipelineTraceContext(**request.trace_context.model_dump())
                    if request.trace_context is not None
                    else None
                ),
            ),
            definition=compiled_definition,
        )
        return PipelineRunEnvelope(
            data=_run_data(
                result,
                diagnostics=compile_result.diagnostics,
            )
        )

    router.add_api_route(
        "/pipeline-blocks",
        get_pipeline_blocks,
        methods=["GET"],
        response_model=PipelineBlockCatalogEnvelope,
    )
    router.add_api_route(
        "/pipeline-definitions/compile",
        compile_pipeline_definition,
        methods=["POST"],
        response_model=PipelineDefinitionCompileEnvelope,
    )
    router.add_api_route(
        "/pipeline-runs",
        run_pipeline_definition,
        methods=["POST"],
        response_model=PipelineRunEnvelope,
    )
    return router


def _compile_command(request: PipelineDefinitionCompileRequest) -> PipelineCompileCommand:
    return PipelineCompileCommand(
        pipeline_id=request.pipeline_id,
        steps=tuple(
            PipelineStepCompileInput(
                step_id=step.step_id,
                implementation_id=step.implementation_id,
                display_name=step.display_name,
                config=step.config,
                failure_policy=FailurePolicy(step.failure_policy),
                enabled=step.enabled,
            )
            for step in request.steps
        ),
    )


def _compile_command_from_definition(
    definition: CompiledPipelineDefinitionSchema,
) -> PipelineCompileCommand:
    return PipelineCompileCommand(
        pipeline_id=definition.pipeline_id,
        steps=tuple(
            PipelineStepCompileInput(
                step_id=step.step_id,
                implementation_id=step.implementation_id,
                display_name=step.display_name,
                config=step.config,
                failure_policy=FailurePolicy(step.failure_policy),
                enabled=step.enabled,
            )
            for step in definition.steps
        ),
    )


def _compile_data(result: PipelineCompileResult) -> PipelineDefinitionCompileData:
    return PipelineDefinitionCompileData(
        valid=result.valid,
        catalog_version=result.catalog_version,
        catalog_hash=result.catalog_hash,
        diagnostics=[_diagnostic_schema(diagnostic) for diagnostic in result.diagnostics],
        compiled_definition=_compiled_definition_schema(result.compiled_definition),
    )


def _compiled_definition_matches_request(
    request_definition: CompiledPipelineDefinitionSchema,
    compiled_definition: PipelineDefinition,
) -> bool:
    canonical_definition = _compiled_definition_schema(compiled_definition)
    if canonical_definition is None:
        return False
    return request_definition.model_dump(mode="json") == canonical_definition.model_dump(
        mode="json"
    )


def _compiled_definition_mismatch_diagnostic() -> PipelineCompileDiagnostic:
    return PipelineCompileDiagnostic(
        severity=PipelineDiagnosticSeverity.ERROR,
        code="COMPILED_DEFINITION_MISMATCH",
        message="Compiled pipeline definition does not match the current catalog output.",
        path="compiled_definition",
    )


def _block_schema(metadata: PipelineBlockMetadata) -> PipelineBlockSchema:
    return PipelineBlockSchema(
        implementation_id=metadata.implementation_id,
        step_type=metadata.step_type,
        display_name=metadata.display_name,
        description=metadata.description,
        status=metadata.status.value,
        category=metadata.category,
        version=metadata.version,
        requires=list(metadata.requires),
        produces=list(metadata.produces),
        default_config=dict(metadata.default_config),
        config_schema=dict(metadata.config_schema),
        ui_hints=dict(metadata.ui_hints),
        allowed_failure_policies=[
            failure_policy.value for failure_policy in metadata.allowed_failure_policies
        ],
    )


def _diagnostic_schema(diagnostic: PipelineCompileDiagnostic) -> PipelineCompileDiagnosticSchema:
    return PipelineCompileDiagnosticSchema(
        severity=diagnostic.severity.value,
        code=diagnostic.code,
        message=diagnostic.message,
        step_id=diagnostic.step_id,
        path=diagnostic.path,
    )


def _compiled_definition_schema(
    definition: PipelineDefinition | None,
) -> CompiledPipelineDefinitionSchema | None:
    if definition is None:
        return None

    return CompiledPipelineDefinitionSchema(
        pipeline_id=definition.pipeline_id,
        steps=[_compiled_step_schema(step) for step in definition.steps],
    )


def _compiled_step_schema(step: PipelineStepDefinition) -> CompiledPipelineStepSchema:
    return CompiledPipelineStepSchema(
        step_id=step.step_id,
        step_type=step.step_type,
        implementation_id=step.implementation_id,
        display_name=step.display_name,
        config=dict(step.config),
        failure_policy=step.failure_policy.value,
        enabled=step.enabled,
    )


def _run_data(
    result: PipelineInvocationResult,
    *,
    diagnostics: tuple[PipelineCompileDiagnostic, ...] = (),
) -> PipelineRunData:
    return PipelineRunData(
        pipeline_id=result.pipeline_id,
        run_id=result.run_id,
        status=result.status.value,
        trace=[_trace_step_schema(step) for step in result.trace],
        metrics=dict(result.metrics),
        diagnostics=[_diagnostic_schema(diagnostic) for diagnostic in diagnostics],
        error=_run_error_schema(result.error),
        ocr_result=_ocr_result_schema(result.ocr_result),
        context_resolution_result=_context_resolution_result_schema(
            result.context_resolution_result
        ),
    )


def _invalid_run_data(
    *,
    request: PipelineRunRequest,
    diagnostics: tuple[PipelineCompileDiagnostic, ...],
) -> PipelineRunData:
    return PipelineRunData(
        pipeline_id=request.compiled_definition.pipeline_id,
        run_id=request.run_id or uuid4().hex,
        status="failed",
        trace=[],
        metrics={
            "step_count": 0,
            "succeeded_step_count": 0,
            "failed_step_count": 0,
            "skipped_step_count": 0,
        },
        diagnostics=[_diagnostic_schema(diagnostic) for diagnostic in diagnostics],
        error=PipelineRunErrorSchema(
            code="PIPELINE_DEFINITION_INVALID",
            message="Compiled pipeline definition is invalid.",
        ),
    )


def _trace_step_schema(step: StepResult) -> PipelineRunTraceStepSchema:
    return PipelineRunTraceStepSchema(
        step_id=step.step_id,
        step_type=step.step_type,
        implementation_id=step.implementation_id,
        status=step.status.value,
        duration_seconds=step.duration_seconds,
        metrics=dict(step.metrics),
        error=_run_error_schema(step.error),
    )


def _run_error_schema(error: StepError | None) -> PipelineRunErrorSchema | None:
    if error is None:
        return None

    return PipelineRunErrorSchema(code=error.code, message=error.message)


def _context_resolution_result_schema(
    result: PipelineInvocationContextResolutionResult | None,
) -> PipelineRunContextResolutionResultSchema | None:
    if result is None:
        return None
    return PipelineRunContextResolutionResultSchema(
        schema_version=result.schema_version,
        status=_context_resolution_status(result.status),
        document_type_id=result.document_type_id,
        total_attribute_count=result.total_attribute_count,
        quality=_context_resolution_quality_schema(result.quality),
        attributes=[
            _context_resolution_attribute_schema(attribute) for attribute in result.attributes
        ],
    )


def _context_resolution_status(value: str) -> PipelineRunStatusSchema:
    if value == "partial_failed":
        return "partial_failed"
    if value == "failed":
        return "failed"
    return "succeeded"


def _context_resolution_quality_schema(
    quality: PipelineInvocationContextResolutionQuality,
) -> PipelineRunContextResolutionQualitySchema:
    return PipelineRunContextResolutionQualitySchema(
        resolved_attribute_count=quality.resolved_attribute_count,
        review_required_attribute_count=quality.review_required_attribute_count,
        missing_required_attribute_count=quality.missing_required_attribute_count,
        missing_attribute_count=quality.missing_attribute_count,
        low_confidence_attribute_count=quality.low_confidence_attribute_count,
        conflicting_attribute_count=quality.conflicting_attribute_count,
    )


def _context_resolution_attribute_schema(
    attribute: PipelineInvocationContextResolutionAttribute,
) -> PipelineRunContextResolutionAttributeSchema:
    return PipelineRunContextResolutionAttributeSchema(
        document_type_id=attribute.document_type_id,
        attribute_external_id=attribute.attribute_external_id,
        attribute_id=attribute.attribute_id,
        display_name=attribute.display_name,
        value_type=attribute.value_type,
        required=attribute.required,
        value=attribute.value,
        confidence_score=attribute.confidence_score,
        status=attribute.status,
        requires_review=attribute.requires_review,
        sources=[_context_resolution_source_schema(source) for source in attribute.sources],
        reason_codes=list(attribute.reason_codes),
        consistency_status=attribute.consistency_status,
        compared_values=list(attribute.compared_values),
        compared_key_value_pages=list(attribute.compared_key_value_pages),
        compared_key_value_indexes=list(attribute.compared_key_value_indexes),
        confidence_before=attribute.confidence_before,
        confidence_after=attribute.confidence_after,
    )


def _context_resolution_source_schema(
    source: PipelineInvocationContextResolutionSource,
) -> PipelineRunContextResolutionSourceSchema:
    return PipelineRunContextResolutionSourceSchema(
        kind=source.kind,
        page_number=source.page_number,
        line_number=source.line_number,
        key_value_index=source.key_value_index,
        confidence=source.confidence,
    )


def _ocr_result_schema(
    result: PipelineInvocationOcrResult | None,
) -> PipelineRunOcrResultSchema | None:
    if result is None:
        return None
    return PipelineRunOcrResultSchema(
        status=result.status,
        provider_id=result.provider_id,
        model_id=result.model_id,
        total_page_count=result.total_page_count,
        succeeded_page_count=result.succeeded_page_count,
        failed_page_count=result.failed_page_count,
        average_confidence=result.average_confidence,
        low_confidence_page_count=result.low_confidence_page_count,
        warning_count=result.warning_count,
        pages_truncated=result.pages_truncated,
        pages=[_ocr_page_result_schema(page) for page in result.pages],
        key_value_pairs_truncated=result.key_value_pairs_truncated,
        key_value_pairs=[_ocr_key_value_pair_schema(pair) for pair in result.key_value_pairs],
    )


def _ocr_page_result_schema(
    page: PipelineInvocationOcrPageResult,
) -> PipelineRunOcrPageResultSchema:
    return PipelineRunOcrPageResultSchema(
        page_number=page.page_number,
        status=page.status,
        text=page.text,
        text_truncated=page.text_truncated,
        lines=list(page.lines),
        lines_truncated=page.lines_truncated,
        confidence=page.confidence,
        warning_codes=list(page.warning_codes),
        error_code=page.error_code,
        fallback_used=page.fallback_used,
        fallback_reason_codes=list(page.fallback_reason_codes),
        primary_error_code=page.primary_error_code,
    )


def _ocr_key_value_pair_schema(
    pair: PipelineInvocationOcrKeyValuePair,
) -> PipelineRunOcrKeyValuePairSchema:
    return PipelineRunOcrKeyValuePairSchema(
        key=pair.key,
        value=pair.value,
        key_truncated=pair.key_truncated,
        value_truncated=pair.value_truncated,
        confidence=pair.confidence,
        page_number=pair.page_number,
        bounding_polygon=list(pair.bounding_polygon),
        order_index=pair.order_index,
        source=pair.source,
    )
