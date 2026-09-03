"""Langfuse observation updates for Context Resolver model generations."""

from collections.abc import Mapping
from typing import Any, cast

from docmind_llmmagic.application.pipeline.observability import ModelIdentity, TraceCaptureMode
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelRequest,
    ContextResolverModelResult,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.prompt import ContextResolverPrompt
from docmind_llmmagic.infrastructure.pipeline.context_resolver.telemetry import (
    ModelResponseMetadata,
    ModelUsage,
    model_trace_metadata,
    provider_error_trace_details,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.trace_projection import (
    failed_trace_output,
    succeeded_trace_output,
)


def update_failed_observation(
    observation: object,
    *,
    request: ContextResolverModelRequest,
    metadata: ModelResponseMetadata | None,
    usage: ModelUsage | None,
    raw_response: str | None,
    model_identity: ModelIdentity,
    prompt: ContextResolverPrompt,
    capture_mode: TraceCaptureMode,
    latency_seconds: float,
    error: Exception,
    request_shape: Mapping[str, object],
    validation_reason: str | None = None,
) -> None:
    """Record a failed generation without violating its capture policy."""

    update_model_failure_observation(
        observation,
        metadata={
            "status": "failed",
            **model_trace_metadata(request),
            **model_identity.metadata(),
            "prompt_version": prompt.version,
            "prompt_sha256": prompt.sha256,
            "capture_mode": capture_mode.value,
            **request_shape,
        },
        capture_mode=capture_mode,
        raw_response=raw_response,
        finish_reason=metadata.finish_reason if metadata is not None else None,
        refusal=metadata.refusal if metadata is not None else False,
        incomplete=metadata.incomplete if metadata is not None else False,
        latency_seconds=latency_seconds,
        error=error,
        usage=usage,
        validation_reason=validation_reason,
        status_message="Model request or response validation failed.",
    )


def update_model_failure_observation(
    observation: object,
    *,
    metadata: Mapping[str, object],
    capture_mode: TraceCaptureMode,
    raw_response: str | None,
    finish_reason: str | None,
    refusal: bool,
    incomplete: bool,
    latency_seconds: float,
    error: Exception,
    usage: ModelUsage | None,
    validation_reason: str | None = None,
    error_code: str | None = None,
    status_message: str = "Model request failed.",
) -> None:
    """Record one model failure through the shared capture-mode policy."""

    error_details = provider_error_trace_details(
        error,
        capture_mode=capture_mode,
        error_code=error_code,
    )
    if validation_reason is not None:
        error_details["validation_reason"] = validation_reason
    update: dict[str, object] = {
        "metadata": dict(metadata),
        "output": failed_trace_output(
            capture_mode=capture_mode,
            raw_response=raw_response,
            finish_reason=finish_reason,
            refusal=refusal,
            incomplete=incomplete,
            latency_seconds=latency_seconds,
            error_details=error_details,
        ),
        "level": "ERROR",
        "status_message": status_message,
    }
    _add_usage(update, usage)
    cast(Any, observation).update(**update)


def update_succeeded_observation(
    observation: object,
    *,
    request: ContextResolverModelRequest,
    result: ContextResolverModelResult,
    raw_response: str,
    metadata: ModelResponseMetadata,
    usage: ModelUsage | None,
    model_identity: ModelIdentity,
    prompt: ContextResolverPrompt,
    capture_mode: TraceCaptureMode,
    latency_seconds: float,
    request_shape: Mapping[str, object],
) -> None:
    """Record a successful generation without violating its capture policy."""

    update: dict[str, object] = {
        "metadata": {
            "status": "succeeded",
            **model_trace_metadata(request),
            **model_identity.metadata(),
            "prompt_version": prompt.version,
            "prompt_sha256": prompt.sha256,
            "capture_mode": capture_mode.value,
            **request_shape,
        },
        "output": succeeded_trace_output(
            capture_mode=capture_mode,
            result=result,
            raw_response=raw_response,
            finish_reason=metadata.finish_reason,
            refusal=metadata.refusal,
            incomplete=metadata.incomplete,
            latency_seconds=latency_seconds,
        ),
    }
    _add_usage(update, usage)
    cast(Any, observation).update(**update)


def _add_usage(update: dict[str, object], usage: ModelUsage | None) -> None:
    usage_details = usage.langfuse_details() if usage is not None else None
    if usage_details is not None:
        update["usage_details"] = usage_details
