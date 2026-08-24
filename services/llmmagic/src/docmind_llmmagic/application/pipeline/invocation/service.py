"""Application use case for invoking configured LLM Magic pipelines."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import uuid4

from docmind_llmmagic.application.pipeline.definitions.default_document import (
    DEFAULT_DOCUMENT_PIPELINE_ID,
)
from docmind_llmmagic.application.pipeline.engine.ports import ProgressCallback
from docmind_llmmagic.application.pipeline.engine.registry import StepFactoryRegistry
from docmind_llmmagic.application.pipeline.engine.runner import PipelineRunner
from docmind_llmmagic.application.pipeline.invocation.context_resolution_result import (
    PipelineInvocationContextResolutionResult,
    context_resolution_result_from_context,
)
from docmind_llmmagic.application.pipeline.invocation.contracts import (
    INVOCATION_INPUT_ARTIFACT_KEY,
    PipelineInvocationInput,
    PipelineTraceContext,
)
from docmind_llmmagic.application.pipeline.invocation.ocr_result import (
    PipelineInvocationOcrResult,
    ocr_result_from_context,
)
from docmind_llmmagic.application.pipeline.observability import (
    PipelineObserver,
    TraceCaptureMode,
)
from docmind_llmmagic.domain.pipeline.models import (
    MetricValue,
    PipelineContext,
    PipelineDefinition,
    PipelineStatus,
    PipelineStepStatus,
    StepError,
    StepResult,
)


def _empty_metadata() -> dict[str, MetricValue]:
    return {}


def _empty_metrics() -> dict[str, MetricValue]:
    return {}


@dataclass(frozen=True, slots=True)
class PipelineInvocationCommand:
    """Command for invoking a named or default document pipeline."""

    document_reference: str
    pipeline_id: str = DEFAULT_DOCUMENT_PIPELINE_ID
    run_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    metadata: Mapping[str, MetricValue] = field(default_factory=_empty_metadata)
    trace_context: PipelineTraceContext | None = None


@dataclass(frozen=True, slots=True)
class PipelineInvocationResult:
    """Safe result returned by the pipeline invocation use case."""

    pipeline_id: str
    run_id: str
    status: PipelineStatus
    trace: tuple[StepResult, ...]
    metrics: Mapping[str, MetricValue] = field(default_factory=_empty_metrics)
    error: StepError | None = None
    ocr_result: PipelineInvocationOcrResult | None = None
    context_resolution_result: PipelineInvocationContextResolutionResult | None = None


class PipelineInvocationService:
    """Run configured pipelines through the existing composable runner."""

    def __init__(
        self,
        *,
        registry: StepFactoryRegistry,
        definitions: Mapping[str, PipelineDefinition],
        observer: PipelineObserver | None = None,
        trace_capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
        trace_metadata: Mapping[str, object] | None = None,
    ) -> None:
        self._runner = PipelineRunner(
            registry,
            observer=observer,
            capture_mode=trace_capture_mode,
        )
        self._definitions = dict(definitions)
        self._trace_metadata = dict(trace_metadata or {})

    async def invoke(
        self,
        command: PipelineInvocationCommand,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineInvocationResult:
        """Invoke the requested pipeline and return a safe read model."""

        run_id = command.run_id or uuid4().hex
        command_error = self._validate_command(command)
        if command_error is not None:
            return self._failed_result(
                pipeline_id=command.pipeline_id,
                run_id=run_id,
                error=command_error,
            )

        definition = self._definitions.get(command.pipeline_id)
        if definition is None:
            return self._failed_result(
                pipeline_id=command.pipeline_id,
                run_id=run_id,
                error=StepError(
                    code="PIPELINE_NOT_FOUND",
                    message="Pipeline definition is not registered.",
                ),
            )

        return await self._invoke_definition(
            command=command,
            definition=definition,
            run_id=run_id,
            progress_callback=progress_callback,
        )

    async def invoke_compiled_definition(
        self,
        command: PipelineInvocationCommand,
        *,
        definition: PipelineDefinition,
        progress_callback: ProgressCallback | None = None,
    ) -> PipelineInvocationResult:
        """Invoke one caller-supplied compiled pipeline definition snapshot."""

        run_id = command.run_id or uuid4().hex
        command_error = self._validate_command(command)
        if command_error is not None:
            return self._failed_result(
                pipeline_id=command.pipeline_id,
                run_id=run_id,
                error=command_error,
            )
        if command.pipeline_id != definition.pipeline_id:
            return self._failed_result(
                pipeline_id=command.pipeline_id,
                run_id=run_id,
                error=StepError(
                    code="PIPELINE_DEFINITION_MISMATCH",
                    message="Pipeline command does not match the compiled definition.",
                ),
            )

        return await self._invoke_definition(
            command=command,
            definition=definition,
            run_id=run_id,
            progress_callback=progress_callback,
        )

    async def _invoke_definition(
        self,
        *,
        command: PipelineInvocationCommand,
        definition: PipelineDefinition,
        run_id: str,
        progress_callback: ProgressCallback | None,
    ) -> PipelineInvocationResult:
        context = PipelineContext(pipeline_id=definition.pipeline_id, run_id=run_id)
        context.add_artifact(
            key=INVOCATION_INPUT_ARTIFACT_KEY,
            value=PipelineInvocationInput(
                document_reference=command.document_reference,
                user_id=command.user_id,
                session_id=command.session_id,
                metadata=dict(command.metadata),
                trace_context=command.trace_context,
            ),
            produced_by_step_id="invocation",
        )

        result = await self._runner.run(
            definition,
            seed_context=context,
            progress_callback=progress_callback,
            trace_user_id=command.user_id,
            trace_session_id=run_id,
            trace_metadata={
                **self._trace_metadata,
                **dict(command.metadata),
                **(command.trace_context.metadata() if command.trace_context is not None else {}),
                "correlation_id": (
                    command.trace_context.correlation_id or command.session_id
                    if command.trace_context is not None
                    else command.session_id
                ),
            },
        )

        return PipelineInvocationResult(
            pipeline_id=result.pipeline_id,
            run_id=result.run_id,
            status=result.status,
            trace=result.trace,
            metrics=self._metrics_for_trace(result.trace),
            error=result.error,
            ocr_result=ocr_result_from_context(result.context),
            context_resolution_result=context_resolution_result_from_context(result.context),
        )

    @staticmethod
    def _validate_command(command: PipelineInvocationCommand) -> StepError | None:
        if not command.pipeline_id:
            return StepError(
                code="PIPELINE_ID_REQUIRED",
                message="Pipeline id is required.",
            )
        if not command.document_reference:
            return StepError(
                code="DOCUMENT_REFERENCE_REQUIRED",
                message="Document reference is required.",
            )

        return None

    @staticmethod
    def _failed_result(
        *,
        pipeline_id: str,
        run_id: str,
        error: StepError,
    ) -> PipelineInvocationResult:
        return PipelineInvocationResult(
            pipeline_id=pipeline_id,
            run_id=run_id,
            status=PipelineStatus.FAILED,
            trace=(),
            metrics={
                "step_count": 0,
                "succeeded_step_count": 0,
                "failed_step_count": 0,
                "skipped_step_count": 0,
            },
            error=error,
        )

    @staticmethod
    def _metrics_for_trace(trace: tuple[StepResult, ...]) -> dict[str, MetricValue]:
        return {
            "step_count": len(trace),
            "succeeded_step_count": sum(
                step.status == PipelineStepStatus.SUCCEEDED for step in trace
            ),
            "failed_step_count": sum(step.status == PipelineStepStatus.FAILED for step in trace),
            "skipped_step_count": sum(step.status == PipelineStepStatus.SKIPPED for step in trace),
        }
