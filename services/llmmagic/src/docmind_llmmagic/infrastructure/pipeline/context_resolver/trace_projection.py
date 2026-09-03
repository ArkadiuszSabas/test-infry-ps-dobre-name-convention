"""Capture-mode-aware Langfuse projections for Context Resolver generations."""

from collections.abc import Mapping
from typing import cast

from docmind_llmmagic.application.pipeline.observability import TraceCaptureMode
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelRequest,
    ContextResolverModelResult,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.prompt import ContextResolverPrompt

_GENERATION_NAMES = {
    "technical_retry": "context-resolver.repair",
    "coverage_fallback": "context-resolver.coverage",
}


def generation_name(repair_kind: str) -> str:
    """Return the stable Langfuse generation name for one request kind."""

    return _GENERATION_NAMES.get(repair_kind, "context-resolver.primary")


def model_trace_input(
    request: ContextResolverModelRequest,
    *,
    prompt: ContextResolverPrompt,
    data: dict[str, object],
    response_format: Mapping[str, object],
    model_id: str,
    request_timeout_seconds: float,
    capture_mode: TraceCaptureMode,
    request_shape: Mapping[str, object],
) -> dict[str, object] | None:
    """Project one typed model request according to the capture policy."""

    if capture_mode is TraceCaptureMode.OFF:
        return None

    contract_name, strict = _contract_identity(response_format)
    parameters = {
        "model": model_id,
        "reasoning_effort": request.reasoning_effort,
        "max_completion_tokens": request.max_completion_tokens,
        "timeout_seconds": request_timeout_seconds,
    }
    correlation = {
        "pipeline_id": request.pipeline_id,
        "run_id": request.run_id,
        "step_id": request.step_id,
        "batch_id": request.batch_id,
        "attempt": request.attempt,
        "repair_kind": request.repair_kind,
    }
    if capture_mode is TraceCaptureMode.FULL:
        return {
            "schema_version": 1,
            "capture_mode": capture_mode.value,
            "prompt": {
                "name": "context-resolver",
                "version": prompt.version,
                "sha256": prompt.sha256,
                "text": prompt.text,
            },
            "data": data,
            "contract": {
                "name": contract_name,
                "strict": strict,
                "response_format": response_format,
            },
            "parameters": parameters,
            "correlation": correlation,
            "preflight": dict(request_shape),
        }

    return {
        "schema_version": 1,
        "capture_mode": capture_mode.value,
        "prompt": {
            "name": "context-resolver",
            "version": prompt.version,
            "sha256": prompt.sha256,
        },
        "data": {
            "attribute_count": len(request.attributes),
            "evidence_count": len(request.evidence),
            "page_count": request.ocr_page_count,
        },
        "contract": {
            "name": contract_name,
            "strict": strict,
        },
        "parameters": parameters,
        "correlation": correlation,
        "preflight": dict(request_shape),
    }


def succeeded_trace_output(
    *,
    capture_mode: TraceCaptureMode,
    result: ContextResolverModelResult,
    raw_response: str,
    finish_reason: str | None,
    refusal: bool,
    incomplete: bool,
    latency_seconds: float,
) -> dict[str, object]:
    """Return a successful generation output without leaking content across modes."""

    output: dict[str, object] = {
        "status": "succeeded",
        "result_count": len(result.attributes),
        "response_char_count": len(raw_response),
        "finish_reason": finish_reason,
        "refusal": refusal,
        "incomplete": incomplete,
        "exact_contract_validation": True,
        "latency_seconds": round(latency_seconds, 6),
    }
    if capture_mode is TraceCaptureMode.FULL:
        output["raw_response"] = raw_response
        output["parsed_response"] = {
            "attributes": [
                {
                    "attribute_external_id": attribute.attribute_external_id,
                    "value": attribute.value,
                    "confidence_score": attribute.confidence_score,
                    "status": attribute.status.value,
                    "evidence_ids": list(attribute.evidence_ids),
                }
                for attribute in result.attributes
            ]
        }
    return output


def failed_trace_output(
    *,
    capture_mode: TraceCaptureMode,
    raw_response: str | None,
    finish_reason: str | None,
    refusal: bool,
    incomplete: bool,
    latency_seconds: float,
    error_details: Mapping[str, object],
) -> dict[str, object]:
    """Return a failed generation output without leaking content across modes."""

    output: dict[str, object] = {
        "status": "failed",
        "finish_reason": finish_reason,
        "refusal": refusal,
        "incomplete": incomplete,
        "exact_contract_validation": False,
        "latency_seconds": round(latency_seconds, 6),
        **error_details,
    }
    if capture_mode is TraceCaptureMode.FULL:
        output["raw_response"] = raw_response
    return output


def _contract_identity(response_format: Mapping[str, object]) -> tuple[str | None, bool]:
    schema_value = response_format.get("json_schema")
    if not isinstance(schema_value, Mapping):
        return None, False
    schema = cast(Mapping[str, object], schema_value)
    name = schema.get("name")
    return (name if isinstance(name, str) else None, schema.get("strict") is True)
