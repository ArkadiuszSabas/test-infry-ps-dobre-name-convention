"""Internal OCR pipeline endpoints for the DocMind.ai LLM Magic service."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, ConfigDict, Field

from docmind_backend_runtime import ApplicationError, get_correlation_id
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
    PipelineRunAcceptedData,
    PipelineRunAcceptedEnvelope,
    PipelineRunRequest,
)
from docmind_llmmagic.application.pipeline.compiler import PipelineDefinitionCompiler
from docmind_llmmagic.application.pipeline.invocation.async_execution import (
    AdmissionError,
    AsyncOcrExecutionService,
    RunKey,
)
from docmind_llmmagic.application.pipeline.invocation.contracts import PipelineTraceContext
from docmind_llmmagic.application.pipeline.invocation.service import PipelineInvocationCommand
from docmind_llmmagic.domain.pipeline.catalog import (
    PipelineBlockMetadata,
    PipelineCompileCommand,
    PipelineCompileDiagnostic,
    PipelineCompileResult,
    PipelineStepCompileInput,
)
from docmind_llmmagic.domain.pipeline.models import (
    FailurePolicy,
    PipelineDefinition,
    PipelineStepDefinition,
)

PipelineCompilerDependency = Callable[[], PipelineDefinitionCompiler]
AsyncOcrExecutionDependency = Callable[..., AsyncOcrExecutionService]


class _CancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fencing_token: int = Field(ge=1)
    next_event_sequence: int = Field(ge=2)
    document_id: UUID
    pipeline_id: UUID
    correlation_id: str


def create_internal_ocr_router(
    *,
    compiler_dependency: PipelineCompilerDependency,
    execution_dependency: AsyncOcrExecutionDependency,
) -> APIRouter:
    """Create the internal OCR router with bootstrap-provided dependencies."""

    router = APIRouter(prefix="/internal/ocr", tags=["internal-ocr"])

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
        execution_service: Annotated[AsyncOcrExecutionService, Depends(execution_dependency)],
        response: Response,
    ) -> PipelineRunAcceptedEnvelope:
        if request.run_id is None or request.trace_context is None:
            raise ApplicationError(
                code="OCR_PIPELINE_RUN_CONTEXT_REQUIRED",
                message="OCR pipeline execution context is required.",
                status_code=422,
            )
        compile_result = compiler.compile(
            _compile_command_from_definition(request.compiled_definition)
        )
        compiled_definition = compile_result.compiled_definition
        if not compile_result.valid or compiled_definition is None:
            raise ApplicationError(
                code="PIPELINE_DEFINITION_INVALID",
                message="Compiled pipeline definition is invalid.",
                status_code=422,
            )

        if not _compiled_definition_matches_request(
            request.compiled_definition,
            compiled_definition,
        ):
            raise ApplicationError(
                code="COMPILED_DEFINITION_MISMATCH",
                message="Compiled pipeline definition is stale.",
                status_code=409,
            )

        run_id = request.run_id
        attempt_id = request.trace_context.attempt_id
        command = PipelineInvocationCommand(
            document_reference=request.document_reference,
            pipeline_id=compiled_definition.pipeline_id,
            run_id=run_id,
            user_id=request.user_id,
            session_id=get_correlation_id(),
            metadata=dict(request.metadata),
            trace_context=PipelineTraceContext(**request.trace_context.model_dump()),
        )
        try:
            execution_service.admit(
                RunKey(
                    run_id=run_id,
                    attempt_id=attempt_id,
                    fencing_token=request.trace_context.fencing_token,
                ),
                command,
                definition=compiled_definition,
            )
        except AdmissionError as error:
            raise ApplicationError(
                code=error.code,
                message=error.message,
                status_code=error.status_code,
            ) from error
        return PipelineRunAcceptedEnvelope(
            data=PipelineRunAcceptedData(run_id=run_id, attempt_id=attempt_id, status="accepted")
        )

    async def cancel_pipeline_run(
        run_id: str,
        attempt_id: str,
        request: _CancelRequest,
        execution_service: Annotated[AsyncOcrExecutionService, Depends(execution_dependency)],
    ) -> Response:
        execution_service.cancel(
            RunKey(
                run_id=run_id,
                attempt_id=attempt_id,
                fencing_token=request.fencing_token,
            ),
            document_id=str(request.document_id),
            pipeline_id=str(request.pipeline_id),
            next_event_sequence=request.next_event_sequence,
            correlation_id=request.correlation_id,
        )
        return Response(status_code=status.HTTP_202_ACCEPTED)

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
        status_code=status.HTTP_202_ACCEPTED,
        response_model=PipelineRunAcceptedEnvelope,
    )
    router.add_api_route(
        "/pipeline-runs/{run_id}/attempts/{attempt_id}/cancel",
        cancel_pipeline_run,
        methods=["POST"],
        status_code=status.HTTP_202_ACCEPTED,
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
