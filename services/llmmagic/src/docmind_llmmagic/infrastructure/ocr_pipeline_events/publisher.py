"""Dapr publisher for LLM Magic-owned OCR pipeline events."""

import asyncio
from collections.abc import Callable
from dataclasses import asdict
from uuid import uuid4

from docmind_backend_runtime import DaprHttpClient
from docmind_backend_runtime.correlation import CORRELATION_ID_HEADER
from docmind_core.ocr_pipeline import (
    OCR_PROCESSING_RESULTS_TOPIC,
    OcrPipelineEventKindV1,
    OcrPipelineEventV1,
    OcrPipelineSafeErrorV1,
    OcrPipelineStatusV1,
    OcrPipelineStepSnapshotV1,
    OcrPipelineStepStatusV1,
)
from docmind_llmmagic.application.pipeline.invocation.async_execution import (
    RetryableCompletionError,
    RunKey,
    StaleCompletionError,
)
from docmind_llmmagic.application.pipeline.invocation.contracts import PipelineTraceContext
from docmind_llmmagic.application.pipeline.invocation.service import (
    PipelineInvocationResult,
)
from docmind_llmmagic.domain.pipeline.models import (
    PipelineProgress,
    PipelineStepProgress,
    StepError,
    StepResult,
)

_PUBSUB_NAME = "docmind-servicebus-pubsub-llmmagic"
_API_APP_ID = "docmind-api"


class OcrPipelineEventPublisher:
    """Publish validated, bounded event envelopes through the local Dapr sidecar."""

    def __init__(self, *, client_factory: Callable[[], DaprHttpClient]) -> None:
        self._client_factory = client_factory
        self._client = None

    def _get_client(self) -> DaprHttpClient:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    async def progress(
        self,
        key: RunKey,
        progress: PipelineProgress,
        sequence: int,
        completed_step_id: str | None,
        trace_context: PipelineTraceContext,
    ) -> None:
        kind = (
            OcrPipelineEventKindV1.STARTED
            if sequence == 1
            else OcrPipelineEventKindV1.STEP_COMPLETED
        )
        event = OcrPipelineEventV1(
            kind=kind,
            event_id=str(uuid4()),
            run_id=key.run_id,
            document_id=trace_context.document_id,
            attempt_id=key.attempt_id,
            fencing_token=trace_context.fencing_token,
            sequence=sequence,
            pipeline_id=progress.pipeline_id,
            pipeline_status=OcrPipelineStatusV1.RUNNING,
            steps=tuple(_step_snapshot(step) for step in progress.steps),
            completed_step_id=(
                None if kind is OcrPipelineEventKindV1.STARTED else completed_step_id
            ),
        )
        response = await self._get_client().publish_event(
            _PUBSUB_NAME,
            OCR_PROCESSING_RESULTS_TOPIC,
            headers={"x-docmind-service-identity": "docmind-llmmagic"},
            json_body=event.model_dump(mode="json"),
        )
        if response.status_code >= 300:
            raise RuntimeError("Dapr rejected OCR pipeline event publication.")

    async def _publish(self, event: OcrPipelineEventV1) -> None:
        response = await self._get_client().publish_event(
            _PUBSUB_NAME,
            OCR_PROCESSING_RESULTS_TOPIC,
            headers={"x-docmind-service-identity": "docmind-llmmagic"},
            json_body=event.model_dump(mode="json"),
        )
        if response.status_code >= 300:
            raise RuntimeError("Dapr rejected OCR pipeline event publication.")

    async def terminal(
        self,
        key: RunKey,
        result: PipelineInvocationResult,
        sequence: int,
        trace_context: PipelineTraceContext,
    ) -> None:
        steps = tuple(_step_snapshot_from_result(step) for step in result.trace)
        status = OcrPipelineStatusV1(result.status.value)
        kind = (
            OcrPipelineEventKindV1.FAILED
            if status is OcrPipelineStatusV1.FAILED
            else OcrPipelineEventKindV1.COMPLETED
        )
        await self._publish(
            OcrPipelineEventV1(
                kind=kind,
                event_id=str(uuid4()),
                run_id=key.run_id,
                document_id=trace_context.document_id,
                attempt_id=key.attempt_id,
                fencing_token=trace_context.fencing_token,
                sequence=sequence,
                pipeline_id=result.pipeline_id,
                pipeline_status=status,
                steps=steps,
                error=_safe_error(result.error),
            )
        )

    async def completion(
        self, key: RunKey, result: PipelineInvocationResult, trace_context: PipelineTraceContext
    ) -> bool:
        payload = {
            "document_id": trace_context.document_id,
            "fencing_token": trace_context.fencing_token,
            "status": result.status.value,
            "steps": [
                {
                    "step_id": step.step_id,
                    "step_type": step.step_type,
                    "implementation_id": step.implementation_id,
                    "display_name": step.display_name or step.step_id,
                    "status": step.status.value,
                    "duration_seconds": step.duration_seconds,
                    "metrics": dict(step.metrics),
                    "error": _safe_error_payload(step.error),
                }
                for step in result.trace
            ],
            "metrics": dict(result.metrics),
            "diagnostics": [],
            "error": _safe_error_payload(result.error),
            "result": _completion_result_payload(result),
        }
        try:
            response = await self._get_client().invoke_method(
                _API_APP_ID,
                f"internal/ocr/pipeline-runs/{key.run_id}/attempts/{key.attempt_id}/complete",
                http_method="POST",
                headers={"x-docmind-service-identity": "docmind-llmmagic"},
                json_body=payload,
            )
        except Exception as error:
            raise RetryableCompletionError("Completion transport failed.") from error
        if response.status_code == 204:
            return True
        if response.status_code == 409:
            raise StaleCompletionError
        if response.status_code in {408, 429} or response.status_code >= 500:
            raise RetryableCompletionError("Completion service is temporarily unavailable.")
        raise RuntimeError(f"Completion returned HTTP {response.status_code}.")

    async def cancelled(
        self,
        key: RunKey,
        document_id: str,
        pipeline_id: str,
        sequence: int,
        correlation_id: str,
    ) -> None:
        """Confirm cancellation to API, then publish the terminal execution event."""
        for attempt, delay in enumerate((0, 1, 2), start=1):
            if delay:
                await asyncio.sleep(delay)
            try:
                response = await self._get_client().invoke_method(
                    _API_APP_ID,
                    f"internal/ocr/pipeline-runs/{key.run_id}/attempts/{key.attempt_id}/cancelled",
                    http_method="POST",
                    headers={
                        "x-docmind-service-identity": "docmind-llmmagic",
                        CORRELATION_ID_HEADER: correlation_id,
                    },
                    json_body={"fencing_token": key.fencing_token},
                )
            except Exception:
                if attempt == 3:
                    return
                continue
            if response.status_code == 204:
                break
            if response.status_code == 409:
                return
            if response.status_code not in {408, 429} and response.status_code < 500:
                return
            if attempt == 3:
                return
        event = OcrPipelineEventV1(
            kind=OcrPipelineEventKindV1.CANCELLED,
            event_id=str(uuid4()),
            run_id=key.run_id,
            document_id=document_id,
            attempt_id=key.attempt_id,
            fencing_token=key.fencing_token,
            sequence=sequence,
            pipeline_id=pipeline_id,
            pipeline_status=OcrPipelineStatusV1.CANCELLED,
            steps=(),
        )
        response = await self._get_client().publish_event(
            _PUBSUB_NAME,
            OCR_PROCESSING_RESULTS_TOPIC,
            headers={
                "x-docmind-service-identity": "docmind-llmmagic",
                CORRELATION_ID_HEADER: correlation_id,
            },
            json_body=event.model_dump(mode="json"),
        )
        if response.status_code >= 300:
            raise RuntimeError("Dapr rejected OCR pipeline event publication.")


def _step_snapshot(step: PipelineStepProgress) -> OcrPipelineStepSnapshotV1:
    return OcrPipelineStepSnapshotV1(
        step_id=step.step_id,
        display_name=step.display_name or step.step_id,
        step_type=step.step_type,
        implementation_id=step.implementation_id,
        status=OcrPipelineStepStatusV1(step.status.value),
        duration_ms=(
            max(0, round(step.duration_seconds * 1000))
            if step.duration_seconds is not None
            else None
        ),
        metrics=dict(step.metrics),
        error=_safe_error(step.error),
    )


def _step_snapshot_from_result(step: StepResult) -> OcrPipelineStepSnapshotV1:
    return OcrPipelineStepSnapshotV1(
        step_id=step.step_id,
        display_name=step.display_name or step.step_id,
        step_type=step.step_type,
        implementation_id=step.implementation_id,
        status=OcrPipelineStepStatusV1(step.status.value),
        duration_ms=max(0, round(step.duration_seconds * 1000)),
        metrics=dict(step.metrics),
        error=_safe_error(step.error),
    )


def _safe_error(error: StepError | None) -> OcrPipelineSafeErrorV1 | None:
    if error is None:
        return None
    return OcrPipelineSafeErrorV1(code=error.code, message=error.message)


def _safe_error_payload(error: StepError | None) -> dict[str, str] | None:
    safe_error = _safe_error(error)
    return safe_error.model_dump(mode="json") if safe_error is not None else None


def _completion_result_payload(result: PipelineInvocationResult) -> dict[str, object] | None:
    if result.ocr_result is None:
        return None
    payload = asdict(result.ocr_result)
    if result.context_resolution_result is not None:
        payload["context_resolution_result"] = asdict(result.context_resolution_result)
    return payload
