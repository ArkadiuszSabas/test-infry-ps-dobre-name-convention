"""Composable pipeline runner for the LLM Magic service."""

import hashlib
import json
import logging
import re
from collections.abc import Mapping
from time import perf_counter
from traceback import extract_tb
from typing import cast
from uuid import uuid4

from docmind_llmmagic.application.pipeline.engine.artifact_observability import (
    changed_artifacts,
    summarize_artifacts,
)
from docmind_llmmagic.application.pipeline.engine.ports import ProgressCallback
from docmind_llmmagic.application.pipeline.engine.registry import StepFactoryRegistry
from docmind_llmmagic.application.pipeline.observability import (
    BestEffortPipelineObserver,
    NoopPipelineObserver,
    ObservationType,
    PipelineObservation,
    PipelineObserver,
    TraceCaptureMode,
)
from docmind_llmmagic.application.pipeline.scores import pipeline_quality_scores
from docmind_llmmagic.application.pipeline.trace_payloads import (
    TracePayloadSerializerRegistry,
    default_trace_payload_serializer_registry,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.models import (
    FailurePolicy,
    MetricValue,
    PipelineArtifact,
    PipelineContext,
    PipelineDefinition,
    PipelineProgress,
    PipelineResult,
    PipelineStatus,
    PipelineStepDefinition,
    PipelineStepProgress,
    PipelineStepStatus,
    StepError,
    StepResult,
)

_SAFE_METRIC_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
_LOGGER = logging.getLogger("docmind_llmmagic.pipeline")


class PipelineRunner:
    """Run an ordered pipeline definition against a shared context."""

    def __init__(
        self,
        registry: StepFactoryRegistry,
        *,
        observer: PipelineObserver | None = None,
        capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
        trace_payloads: TracePayloadSerializerRegistry | None = None,
    ) -> None:
        self._registry = registry
        self._observer = BestEffortPipelineObserver(observer or NoopPipelineObserver())
        self._capture_mode = capture_mode
        self._trace_payloads = trace_payloads or default_trace_payload_serializer_registry()

    async def run(
        self,
        definition: PipelineDefinition,
        *,
        seed_context: PipelineContext | None = None,
        progress_callback: ProgressCallback | None = None,
        trace_user_id: str | None = None,
        trace_session_id: str | None = None,
        trace_metadata: Mapping[str, object] | None = None,
    ) -> PipelineResult:
        """Run a pipeline definition after validating all configured steps."""

        run_context = seed_context or PipelineContext(
            pipeline_id=definition.pipeline_id,
            run_id=uuid4().hex,
        )
        root_metadata = self._trace_payloads.serialize_metadata(
            {
                "pipeline_id": definition.pipeline_id,
                "run_id": run_context.run_id,
                **dict(trace_metadata or {}),
            }
        )
        root_input: dict[str, object] | None = None
        trace_input: dict[str, object] | None = None
        if self._capture_mode is not TraceCaptureMode.OFF:
            serialized_definition = self._trace_payloads.serialize_definition(definition)
            root_input = {
                "definition": serialized_definition,
                "artifacts": self._trace_payloads.serialize_artifacts(
                    run_context.artifacts,
                    capture_mode=self._capture_mode,
                ),
            }
            trace_input = {
                "schema_version": 2,
                "pipeline_id": definition.pipeline_id,
                "run_id": run_context.run_id,
                "user_id": trace_user_id,
                "step_count": len(definition.steps),
                "definition_sha256": _payload_sha256(serialized_definition),
                "initial_artifact_count": len(run_context.artifacts),
                "context": root_metadata,
            }
        started_at = perf_counter()
        with self._observer.observe(
            observation_type=ObservationType.CHAIN,
            name="ocr-pipeline-run",
            trace_name="ocr-pipeline-run",
            user_id=trace_user_id,
            session_id=trace_session_id or run_context.run_id,
            trace_io=False,
            input_data=root_input,
            metadata=root_metadata,
        ) as observation:
            if trace_input is not None:
                observation.update_trace(input=trace_input)
            result = await self._run_validated(
                definition,
                run_context=run_context,
                progress_callback=progress_callback,
            )
            duration_seconds = perf_counter() - started_at
            full_output = self._trace_payloads.serialize_result(
                result,
                capture_mode=self._capture_mode,
            )
            quality_scores = pipeline_quality_scores(result)
            failed_step_count = sum(
                step.status == PipelineStepStatus.FAILED for step in result.trace
            )
            observation.update(
                output=full_output,
                metadata={
                    **root_metadata,
                    "status": result.status.value,
                    "step_count": len(result.trace),
                    "failed_step_count": failed_step_count,
                },
                level="ERROR" if result.status == PipelineStatus.FAILED else "DEFAULT",
                status_message=result.error.message if result.error is not None else None,
            )
            if self._capture_mode is not TraceCaptureMode.OFF:
                observation.update_trace(
                    output={
                        "schema_version": 2,
                        "pipeline_id": result.pipeline_id,
                        "run_id": result.run_id,
                        "status": result.status.value,
                        "duration_seconds": duration_seconds,
                        "step_count": len(result.trace),
                        "failed_step_count": failed_step_count,
                        "step_status_counts": _step_status_counts(result),
                        "quality_scores": quality_scores,
                        "final_artifacts": [
                            {
                                "artifact_key": key,
                                "produced_by_step_id": artifact.produced_by_step_id,
                            }
                            for key, artifact in sorted(result.context.artifacts.items())
                        ],
                        "error": (
                            {
                                "code": result.error.code,
                                "message": result.error.message,
                            }
                            if result.error is not None
                            else None
                        ),
                    }
                )
            for score_name, score_value in quality_scores.items():
                self._observer.score_trace(
                    name=score_name,
                    value=score_value,
                    metadata={
                        "pipeline_id": definition.pipeline_id,
                        "run_id": run_context.run_id,
                    },
                )
            return result

    async def _run_validated(
        self,
        definition: PipelineDefinition,
        *,
        run_context: PipelineContext,
        progress_callback: ProgressCallback | None,
    ) -> PipelineResult:
        validation_error = self._validate(definition)
        if validation_error is not None:
            return self._failed_result(definition, run_context, validation_error)

        context_error = self._validate_seed_context(definition, run_context)
        if context_error is not None:
            return self._failed_result(definition, run_context, context_error)

        progress = _ProgressState(definition=definition, context=run_context)
        await self._emit_progress(progress_callback, progress.snapshot())

        trace: list[StepResult] = []
        has_optional_failure = False

        for step_index, step_definition in enumerate(definition.steps):
            if not step_definition.enabled:
                skipped_result = self._skipped_result(step_definition)
                trace.append(skipped_result)
                self._observe_skipped_step(step_definition, run_context, skipped_result)
                continue

            progress.set_status(step_definition.step_id, PipelineStepStatus.RUNNING)
            await self._emit_progress(progress_callback, progress.snapshot())

            step_result = await self._run_step(step_definition, run_context)
            trace.append(step_result)

            if step_result.status == PipelineStepStatus.SUCCEEDED:
                progress.set_status(step_definition.step_id, PipelineStepStatus.SUCCEEDED)
                await self._emit_progress(progress_callback, progress.snapshot())
                continue

            progress.set_status(step_definition.step_id, PipelineStepStatus.FAILED)
            if step_definition.failure_policy == FailurePolicy.OPTIONAL:
                has_optional_failure = True
                await self._emit_progress(progress_callback, progress.snapshot())
                continue

            skipped_results = self._skip_remaining(definition.steps[step_index + 1 :], progress)
            trace.extend(skipped_results)
            await self._emit_progress(progress_callback, progress.snapshot())

            return PipelineResult(
                pipeline_id=definition.pipeline_id,
                run_id=run_context.run_id,
                status=PipelineStatus.FAILED,
                context=run_context,
                trace=tuple(trace),
                error=step_result.error,
            )

        status = PipelineStatus.PARTIAL_FAILED if has_optional_failure else PipelineStatus.SUCCEEDED

        return PipelineResult(
            pipeline_id=definition.pipeline_id,
            run_id=run_context.run_id,
            status=status,
            context=run_context,
            trace=tuple(trace),
        )

    def _validate(self, definition: PipelineDefinition) -> StepError | None:
        seen_step_ids: set[str] = set()

        if not definition.pipeline_id:
            return StepError(
                code="PIPELINE_ID_REQUIRED",
                message="Pipeline id is required.",
            )

        for step_definition in definition.steps:
            if not step_definition.step_id:
                return StepError(
                    code="STEP_ID_REQUIRED",
                    message="Pipeline step id is required.",
                )
            if step_definition.step_id in seen_step_ids:
                return StepError(
                    code="DUPLICATE_STEP_ID",
                    message="Pipeline step ids must be unique.",
                )
            seen_step_ids.add(step_definition.step_id)

            if step_definition.enabled and not self._registry.has(
                step_definition.implementation_id
            ):
                return StepError(
                    code="UNKNOWN_STEP",
                    message="Pipeline step implementation is not registered.",
                )

        return None

    async def _run_step(
        self,
        definition: PipelineStepDefinition,
        context: PipelineContext,
    ) -> StepResult:
        started_at = perf_counter()
        input_artifacts = dict(context.artifacts)
        with self._observer.observe(
            observation_type=ObservationType.SPAN,
            name=f"pipeline.{definition.step_type}",
            input_data=self._trace_payloads.serialize_artifact_references(
                input_artifacts,
                capture_mode=self._capture_mode,
            ),
            metadata=self._step_metadata(definition, context),
        ) as observation:
            try:
                step = self._registry.create(definition)
                output = await step.run(context, definition)
            except Exception as exc:
                _LOGGER.exception(
                    "Pipeline step execution failed.",
                    extra={
                        "pipeline_id": context.pipeline_id,
                        "run_id": context.run_id,
                        "step_id": definition.step_id,
                        "implementation_id": definition.implementation_id,
                        "error_type": type(exc).__name__,
                    },
                )
                result = StepResult(
                    step_id=definition.step_id,
                    step_type=definition.step_type,
                    implementation_id=definition.implementation_id,
                    status=PipelineStepStatus.FAILED,
                    duration_seconds=perf_counter() - started_at,
                    metrics={},
                    error=self._safe_error(exc),
                )
                self._finish_step_observation(
                    observation,
                    definition=definition,
                    context=context,
                    result=result,
                    input_artifacts=input_artifacts,
                    exception=exc,
                )
                self._log_step_execution(
                    definition=definition,
                    context=context,
                    result=result,
                    input_artifacts=input_artifacts,
                )
                return result

            result = StepResult(
                step_id=definition.step_id,
                step_type=definition.step_type,
                implementation_id=definition.implementation_id,
                status=PipelineStepStatus.SUCCEEDED,
                duration_seconds=perf_counter() - started_at,
                metrics=self._safe_metrics(cast(Mapping[object, object], output.metrics)),
            )
            self._finish_step_observation(
                observation,
                definition=definition,
                context=context,
                result=result,
                input_artifacts=input_artifacts,
                exception=None,
            )
            self._log_step_execution(
                definition=definition,
                context=context,
                result=result,
                input_artifacts=input_artifacts,
            )
            return result

    def _finish_step_observation(
        self,
        observation: PipelineObservation,
        *,
        definition: PipelineStepDefinition,
        context: PipelineContext,
        result: StepResult,
        input_artifacts: Mapping[str, PipelineArtifact],
        exception: Exception | None,
    ) -> None:
        output_artifacts = changed_artifacts(input_artifacts, context.artifacts)
        observation.update(
            output={
                "artifacts": self._trace_payloads.serialize_artifacts(
                    output_artifacts,
                    capture_mode=self._capture_mode,
                ),
                "metrics": dict(result.metrics),
                "error": (
                    {
                        "code": result.error.code,
                        "message": result.error.message,
                        "exception": self._safe_exception_details(exception),
                    }
                    if result.error is not None
                    else None
                ),
            },
            metadata={
                **self._step_metadata(definition, context),
                "status": result.status.value,
                "duration_seconds": result.duration_seconds,
                **dict(result.metrics),
            },
            level="ERROR" if result.status == PipelineStepStatus.FAILED else "DEFAULT",
            status_message=result.error.message if result.error is not None else None,
        )

    @staticmethod
    def _safe_exception_details(exception: Exception | None) -> dict[str, object] | None:
        if exception is None:
            return None
        exception_type = type(exception)
        return {
            "type": f"{exception_type.__module__}.{exception_type.__qualname__}",
            "stack": [
                {
                    "file": frame.filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1],
                    "line": frame.lineno,
                    "function": frame.name,
                }
                for frame in extract_tb(exception.__traceback__)[-20:]
            ],
        }

    def _observe_skipped_step(
        self,
        definition: PipelineStepDefinition,
        context: PipelineContext,
        result: StepResult,
    ) -> None:
        with self._observer.observe(
            observation_type=ObservationType.SPAN,
            name=f"pipeline.{definition.step_type}",
            input_data=self._trace_payloads.serialize_artifact_references(
                context.artifacts,
                capture_mode=self._capture_mode,
            ),
            metadata=self._step_metadata(definition, context),
        ) as observation:
            observation.update(
                output={"status": result.status.value},
                metadata={
                    **self._step_metadata(definition, context),
                    "status": result.status.value,
                },
            )

    @staticmethod
    def _step_metadata(
        definition: PipelineStepDefinition,
        context: PipelineContext,
    ) -> dict[str, object]:
        return {
            "pipeline_id": context.pipeline_id,
            "run_id": context.run_id,
            "step_id": definition.step_id,
            "step_type": definition.step_type,
            "implementation_id": definition.implementation_id,
            "failure_policy": definition.failure_policy.value,
        }

    @staticmethod
    def _log_step_execution(
        *,
        definition: PipelineStepDefinition,
        context: PipelineContext,
        result: StepResult,
        input_artifacts: Mapping[str, PipelineArtifact],
    ) -> None:
        output_artifacts = changed_artifacts(input_artifacts, context.artifacts)
        log_method = _LOGGER.warning if result.status == PipelineStepStatus.FAILED else _LOGGER.info
        log_method(
            "Pipeline step execution completed.",
            extra={
                "event_name": "pipeline.step.completed",
                "pipeline_id": context.pipeline_id,
                "run_id": context.run_id,
                "step_id": definition.step_id,
                "step_type": definition.step_type,
                "implementation_id": definition.implementation_id,
                "step_status": result.status.value,
                "duration_seconds": result.duration_seconds,
                "step_metrics": dict(result.metrics),
                "error_code": result.error.code if result.error is not None else None,
                "pipeline_step_inputs": summarize_artifacts(input_artifacts),
                "pipeline_step_outputs": summarize_artifacts(output_artifacts),
            },
        )
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Pipeline step artifact details.",
                extra={
                    "event_name": "pipeline.step.artifacts",
                    "pipeline_id": context.pipeline_id,
                    "run_id": context.run_id,
                    "step_id": definition.step_id,
                    "implementation_id": definition.implementation_id,
                    "pipeline_step_inputs": summarize_artifacts(
                        input_artifacts,
                        detailed=True,
                    ),
                    "pipeline_step_outputs": summarize_artifacts(
                        output_artifacts,
                        detailed=True,
                    ),
                },
            )

    @staticmethod
    async def _emit_progress(
        progress_callback: ProgressCallback | None,
        progress: PipelineProgress,
    ) -> None:
        if progress_callback is None:
            return

        callback_result = progress_callback(progress)
        if callback_result is not None:
            await callback_result

    @staticmethod
    def _safe_error(exc: Exception) -> StepError:
        if isinstance(exc, PipelineStepError):
            return StepError(code=exc.code, message=exc.message)

        return StepError(
            code="STEP_FAILED",
            message="Pipeline step failed.",
        )

    @staticmethod
    def _safe_metrics(metrics: Mapping[object, object]) -> dict[str, MetricValue]:
        return {
            key: value
            for key, value in metrics.items()
            if isinstance(key, str)
            and _SAFE_METRIC_KEY_PATTERN.fullmatch(key)
            and isinstance(value, bool | int | float)
        }

    @staticmethod
    def _validate_seed_context(
        definition: PipelineDefinition,
        context: PipelineContext,
    ) -> StepError | None:
        if context.pipeline_id != definition.pipeline_id:
            return StepError(
                code="PIPELINE_CONTEXT_MISMATCH",
                message="Pipeline context does not match the pipeline definition.",
            )

        return None

    @staticmethod
    def _failed_result(
        definition: PipelineDefinition,
        context: PipelineContext,
        error: StepError,
    ) -> PipelineResult:
        return PipelineResult(
            pipeline_id=definition.pipeline_id,
            run_id=context.run_id,
            status=PipelineStatus.FAILED,
            context=context,
            trace=(),
            error=error,
        )

    @staticmethod
    def _skipped_result(definition: PipelineStepDefinition) -> StepResult:
        return StepResult(
            step_id=definition.step_id,
            step_type=definition.step_type,
            implementation_id=definition.implementation_id,
            status=PipelineStepStatus.SKIPPED,
            duration_seconds=0.0,
            metrics={},
        )

    def _skip_remaining(
        self,
        remaining_steps: tuple[PipelineStepDefinition, ...],
        progress: _ProgressState,
    ) -> tuple[StepResult, ...]:
        skipped_results: list[StepResult] = []

        for step_definition in remaining_steps:
            progress.set_status(step_definition.step_id, PipelineStepStatus.SKIPPED)
            skipped_result = self._skipped_result(step_definition)
            skipped_results.append(skipped_result)
            self._observe_skipped_step(step_definition, progress.context, skipped_result)

        return tuple(skipped_results)


def _payload_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _step_status_counts(result: PipelineResult) -> dict[str, int]:
    counts = {status.value: 0 for status in PipelineStepStatus}
    for step in result.trace:
        counts[step.status.value] += 1
    return counts


class _ProgressState:
    """Mutable progress state used to emit full snapshots."""

    def __init__(self, *, definition: PipelineDefinition, context: PipelineContext) -> None:
        self._definition = definition
        self._context = context
        self._statuses = {
            step.step_id: PipelineStepStatus.PENDING if step.enabled else PipelineStepStatus.SKIPPED
            for step in definition.steps
        }

    def set_status(self, step_id: str, status: PipelineStepStatus) -> None:
        """Set progress status for one configured step."""

        self._statuses[step_id] = status

    @property
    def context(self) -> PipelineContext:
        """Return the pipeline context used by skipped-step observations."""

        return self._context

    def snapshot(self) -> PipelineProgress:
        """Return a full progress snapshot for every configured step."""

        return PipelineProgress(
            pipeline_id=self._definition.pipeline_id,
            run_id=self._context.run_id,
            steps=tuple(
                PipelineStepProgress(
                    step_id=step.step_id,
                    step_type=step.step_type,
                    implementation_id=step.implementation_id,
                    status=self._statuses[step.step_id],
                )
                for step in self._definition.steps
            ),
        )
