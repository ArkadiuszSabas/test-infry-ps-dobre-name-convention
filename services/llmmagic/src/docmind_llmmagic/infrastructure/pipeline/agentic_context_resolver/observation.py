"""Capture-mode-aware Langfuse projections for Agentic Context Resolver turns."""

from collections.abc import Mapping
from typing import Any, cast

from docmind_llmmagic.application.pipeline.observability import (
    ModelIdentity,
    TraceCaptureMode,
)
from docmind_llmmagic.application.pipeline.steps.document_agentic_context_resolver.ports import (
    AgenticModelRequest,
    AgenticModelTurn,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.observation import (
    update_model_failure_observation,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.telemetry import ModelUsage


def agentic_trace_input(
    request: AgenticModelRequest,
    *,
    create_kwargs: Mapping[str, object],
    capture_mode: TraceCaptureMode,
    request_bytes: int,
) -> dict[str, object] | None:
    """Project one Agentic turn request according to the shared capture mode."""

    if capture_mode is TraceCaptureMode.OFF:
        return None
    result: dict[str, object] = {
        "schema_version": 1,
        "capture_mode": capture_mode.value,
        "correlation": {
            "pipeline_id": request.pipeline_id,
            "run_id": request.run_id,
            "step_id": request.step_id,
            "group_id": request.group_id,
            "turn": request.turn,
        },
        "request_shape": {
            "request_bytes": request_bytes,
            "target_count": len(request.targets),
            "document_view_char_count": len(request.document_view.text),
            "document_view_page_count": len(request.document_view.pages),
            "document_view_segment_count": len(request.document_view.segments),
            "repair": request.repair_message is not None,
        },
        "parameters": {
            "model": create_kwargs["model"],
            "max_completion_tokens": request.max_completion_tokens,
        },
    }
    if capture_mode is TraceCaptureMode.FULL:
        result["provider_request"] = dict(create_kwargs)
    return result


def agentic_trace_metadata(
    request: AgenticModelRequest,
    *,
    model_identity: ModelIdentity,
    capture_mode: TraceCaptureMode,
    request_bytes: int,
    status: str,
) -> dict[str, object]:
    """Return filterable metadata without duplicating the full provider request."""

    return {
        "status": status,
        "resolver": "agentic",
        "pipeline_id": request.pipeline_id,
        "run_id": request.run_id,
        "step_id": request.step_id,
        "group_id": request.group_id,
        "turn": request.turn,
        "target_count": len(request.targets),
        "document_view_char_count": len(request.document_view.text),
        "document_view_page_count": len(request.document_view.pages),
        "document_view_segment_count": len(request.document_view.segments),
        "request_bytes": request_bytes,
        "capture_mode": capture_mode.value,
        **model_identity.metadata(),
    }


def update_agentic_succeeded_observation(
    observation: object,
    *,
    request: AgenticModelRequest,
    turn: AgenticModelTurn,
    model_identity: ModelIdentity,
    capture_mode: TraceCaptureMode,
    request_bytes: int,
    latency_seconds: float,
    usage: ModelUsage | None,
    raw_response: str | None,
) -> None:
    """Record one successful quote-grounded final-result model turn."""

    turn_kind = "invalid_output" if turn.output_error_code is not None else "final_result"
    output: dict[str, object] = {
        "status": "invalid_output" if turn.output_error_code is not None else "succeeded",
        "turn_kind": turn_kind,
        "result_count": len(turn.results),
        "latency_seconds": round(latency_seconds, 6),
        "finish_reason": turn.finish_reason,
        "truncated_response_count": turn.truncated_response_count,
    }
    if turn.output_error_code is not None:
        output["validation_reason"] = turn.output_error_code
    if capture_mode is TraceCaptureMode.FULL:
        output["results"] = [
            {
                "handle": result.handle,
                "status": result.status,
                "candidates": [
                    {
                        "value": candidate.value,
                        "derivation": candidate.derivation,
                        "confidence": candidate.confidence,
                        "evidence": [
                            {"quote": evidence.quote, "page": evidence.page}
                            for evidence in candidate.evidence
                        ],
                    }
                    for candidate in result.candidates
                ],
                "selected_candidate": result.selected_candidate,
            }
            for result in turn.results
        ]
        if raw_response is not None:
            output["raw_response"] = raw_response
    update: dict[str, object] = {
        "metadata": agentic_trace_metadata(
            request,
            model_identity=model_identity,
            capture_mode=capture_mode,
            request_bytes=request_bytes,
            status="succeeded",
        ),
        "output": output,
    }
    usage_details = usage.langfuse_details() if usage is not None else None
    if usage_details is not None:
        update["usage_details"] = usage_details
    cast(Any, observation).update(**update)


def update_agentic_failed_observation(
    observation: object,
    *,
    request: AgenticModelRequest,
    model_identity: ModelIdentity,
    capture_mode: TraceCaptureMode,
    request_bytes: int,
    latency_seconds: float,
    error: Exception,
    usage: ModelUsage | None,
    raw_response: str | None,
    error_code: str,
    validation_reason: str | None = None,
) -> None:
    """Record one Agentic failure through the shared provider-error projection."""

    update_model_failure_observation(
        observation,
        metadata=agentic_trace_metadata(
            request,
            model_identity=model_identity,
            capture_mode=capture_mode,
            request_bytes=request_bytes,
            status="failed",
        ),
        capture_mode=capture_mode,
        raw_response=raw_response,
        finish_reason=None,
        refusal=False,
        incomplete=False,
        latency_seconds=latency_seconds,
        error=error,
        usage=usage,
        validation_reason=validation_reason,
        error_code=error_code,
        status_message="Agentic Context Resolver model turn failed.",
    )
