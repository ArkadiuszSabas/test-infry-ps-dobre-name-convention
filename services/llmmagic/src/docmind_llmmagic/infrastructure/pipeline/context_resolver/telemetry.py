"""PII-safe telemetry helpers for Context Resolver model batches."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import TracebackType
from typing import cast

from docmind_llmmagic.application.pipeline.observability import TraceCaptureMode
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelRequest,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.infrastructure.pipeline.context_resolver.provider_errors import (
    provider_request_error,
)

_MAX_LOG_IDENTIFIER_LENGTH = 200
_MAX_PROVIDER_DEBUG_CHARS = 16_000
_MAX_PROVIDER_DEBUG_DEPTH = 6
_MAX_PROVIDER_DEBUG_ITEMS = 100
_REDACTED = "<redacted>"
_SENSITIVE_DEBUG_KEYS = frozenset(
    {
        "api-key",
        "api_key",
        "access_token",
        "authorization",
        "client-secret",
        "client_secret",
        "credential",
        "ocp-apim-subscription-key",
        "password",
        "refresh_token",
        "secret",
        "subscription-key",
        "token",
        "x-api-key",
    }
)
_LOGGER = logging.getLogger("docmind_llmmagic.context_resolver")


@dataclass(frozen=True, slots=True)
class ModelUsage:
    """Provider token counters; absent counters remain absent rather than becoming zero."""

    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None

    def langfuse_details(self) -> dict[str, int] | None:
        uncached_input = _exclusive_tokens(self.input_tokens, self.cached_input_tokens)
        visible_output = _exclusive_tokens(self.output_tokens, self.reasoning_tokens)
        values = {
            "input": uncached_input,
            "input_cached_tokens": self.cached_input_tokens,
            "output": visible_output,
            "output_reasoning": self.reasoning_tokens,
            "total": self.total_tokens,
        }
        result = {key: value for key, value in values.items() if value is not None}
        return result or None


def _exclusive_tokens(total: int | None, subset: int | None) -> int | None:
    if total is None:
        return None
    return max(0, total - (subset or 0))


@dataclass(frozen=True, slots=True)
class ModelResponseMetadata:
    """Safe completion state for one provider response."""

    finish_reason: str | None
    refusal: bool
    incomplete: bool
    provider_request_id: str | None


def model_trace_metadata(request: ContextResolverModelRequest) -> dict[str, object]:
    """Return allowlisted batch controls without OCR, field names, or values."""

    return {
        "pipeline_id": request.pipeline_id,
        "run_id": request.run_id,
        "step_id": request.step_id,
        "provider_id": "openai",
        "batch_id": request.batch_id,
        "attempt": request.attempt,
        "attribute_count": len(request.attributes),
        "ocr_page_count": request.ocr_page_count,
        "evidence_unit_count": len(request.evidence),
        "evidence_char_count": sum(len(unit.text) for unit in request.evidence),
        "rejected_candidate_count": request.rejected_candidate_count,
        "truncated_candidate_count": request.truncated_candidate_count,
        "reasoning_effort": request.reasoning_effort,
        "max_completion_tokens": request.max_completion_tokens,
        "repair_kind": request.repair_kind,
    }


def model_usage(response: object) -> ModelUsage | None:
    """Read Chat Completions usage including cached and reasoning token details."""

    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return ModelUsage(
        input_tokens=_non_negative_int(_field(usage, "prompt_tokens")),
        cached_input_tokens=_non_negative_int(
            _field(_field(usage, "prompt_tokens_details"), "cached_tokens")
        ),
        output_tokens=_non_negative_int(_field(usage, "completion_tokens")),
        reasoning_tokens=_non_negative_int(
            _field(_field(usage, "completion_tokens_details"), "reasoning_tokens")
        ),
        total_tokens=_non_negative_int(_field(usage, "total_tokens")),
    )


def response_metadata(response: object) -> ModelResponseMetadata:
    """Read finish/refusal/incomplete state and a safe successful request id."""

    choice = _first_choice(response)
    message = getattr(choice, "message", None)
    finish_reason = _safe_log_identifier(getattr(choice, "finish_reason", None))
    refusal = bool(getattr(message, "refusal", None))
    status = _safe_log_identifier(getattr(response, "status", None))
    return ModelResponseMetadata(
        finish_reason=finish_reason,
        refusal=refusal,
        incomplete=status == "incomplete" or finish_reason == "length",
        provider_request_id=_safe_log_identifier(
            getattr(response, "_request_id", None) or getattr(response, "request_id", None)
        ),
    )


def log_model_request_started(
    *,
    request: ContextResolverModelRequest,
    model_id: str,
    request_timeout_seconds: float,
    request_shape: Mapping[str, object],
) -> None:
    _LOGGER.info(
        "Context Resolver model batch started.",
        extra={
            "event_name": "context_resolver.model_batch.started",
            "model_id": model_id,
            "request_timeout_seconds": request_timeout_seconds,
            **request_shape,
            **model_trace_metadata(request),
        },
    )


def log_model_preflight_rejected(
    *,
    error: PipelineStepError,
    request: ContextResolverModelRequest,
    model_id: str,
    request_timeout_seconds: float,
    request_shape: Mapping[str, object],
) -> None:
    """Log a content-free rejection that happened before any provider I/O."""

    _LOGGER.warning(
        "Context Resolver model batch rejected by preflight.",
        extra={
            "event_name": "context_resolver.model_batch.preflight_rejected",
            "error_code": error.code,
            "model_id": model_id,
            "request_timeout_seconds": request_timeout_seconds,
            "provider_call_attempted": False,
            **request_shape,
            **model_trace_metadata(request),
        },
    )


def log_model_request_completed(
    *,
    request: ContextResolverModelRequest,
    model_id: str,
    latency_seconds: float,
    response_char_count: int,
    result_count: int,
    metadata: ModelResponseMetadata,
    usage: ModelUsage | None,
    request_shape: Mapping[str, object],
) -> None:
    _LOGGER.info(
        "Context Resolver model batch completed.",
        extra={
            "event_name": "context_resolver.model_batch.completed",
            "model_id": model_id,
            "latency_seconds": round(latency_seconds, 6),
            "response_char_count": response_char_count,
            "result_count": result_count,
            "finish_reason": metadata.finish_reason,
            "refusal": metadata.refusal,
            "incomplete": metadata.incomplete,
            "provider_request_id": metadata.provider_request_id,
            "exact_contract_validation": True,
            **request_shape,
            **_usage_log_fields(usage),
            **model_trace_metadata(request),
        },
    )


def log_model_request_failure(
    *,
    error: Exception,
    error_code: str,
    request: ContextResolverModelRequest,
    model_id: str,
    request_timeout_seconds: float,
    latency_seconds: float,
    metadata: ModelResponseMetadata | None,
    usage: ModelUsage | None,
    request_shape: Mapping[str, object],
    validation_reason: str | None = None,
) -> None:
    _LOGGER.error(
        "Context Resolver model batch failed.",
        exc_info=_safe_exc_info(error),
        extra={
            "event_name": "context_resolver.model_batch.failed",
            "error_code": error_code,
            "model_id": model_id,
            "request_timeout_seconds": request_timeout_seconds,
            "latency_seconds": round(latency_seconds, 6),
            "finish_reason": metadata.finish_reason if metadata is not None else None,
            "refusal": metadata.refusal if metadata is not None else False,
            "incomplete": metadata.incomplete if metadata is not None else False,
            "provider_status_code": _provider_status_code(error),
            "provider_error_code": _provider_error_code(error),
            "provider_request_id": (
                metadata.provider_request_id
                if metadata is not None and metadata.provider_request_id is not None
                else _provider_request_id(error)
            ),
            "exception_type": _exception_type(error),
            "exception_chain_types": _exception_chain_types(error),
            "exact_contract_validation": False,
            "validation_reason": validation_reason,
            **request_shape,
            **_usage_log_fields(usage),
            **model_trace_metadata(request),
        },
    )


def provider_error_metadata(error: Exception) -> dict[str, object]:
    """Return content-free failure identifiers safe for METADATA Langfuse capture."""

    return {
        "error_code": (
            error.code
            if isinstance(error, PipelineStepError)
            else provider_request_error(error).code
        ),
        "provider_status_code": _provider_status_code(error),
        "provider_error_code": _provider_error_code(error),
        "provider_request_id": _provider_request_id(error),
    }


def provider_error_trace_details(
    error: Exception,
    *,
    capture_mode: TraceCaptureMode,
    error_code: str | None = None,
) -> dict[str, object]:
    """Project one provider failure consistently for every Context Resolver."""

    details = {
        **provider_error_metadata(error),
        "exception_type": _exception_type(error),
        "exception_chain_types": list(_exception_chain_types(error)),
    }
    if error_code is not None:
        details["error_code"] = error_code
    if capture_mode is not TraceCaptureMode.FULL:
        return details

    message, message_truncated = _bounded_debug_text(str(error))
    if message:
        details["provider_error_message"] = message
    body = getattr(error, "body", None)
    body_text, body_truncated = _provider_debug_body(body)
    if body_text is not None:
        details["provider_error_body"] = body_text
    details["provider_error_debug_truncated"] = message_truncated or body_truncated
    return details


def _usage_log_fields(usage: ModelUsage | None) -> dict[str, int | None]:
    return {
        "input_tokens": usage.input_tokens if usage is not None else None,
        "cached_input_tokens": usage.cached_input_tokens if usage is not None else None,
        "output_tokens": usage.output_tokens if usage is not None else None,
        "reasoning_tokens": usage.reasoning_tokens if usage is not None else None,
        "total_tokens": usage.total_tokens if usage is not None else None,
    }


def _first_choice(response: object) -> object:
    choices = getattr(response, "choices", ())
    if isinstance(choices, Sequence) and choices:
        return cast(Sequence[object], choices)[0]
    raise ValueError("missing response choice")


def _field(value: object, name: str) -> object:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value).get(name)
    return getattr(value, name, None)


def _non_negative_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _provider_status_code(error: Exception) -> int | None:
    for value in (
        getattr(error, "status_code", None),
        getattr(getattr(error, "response", None), "status_code", None),
    ):
        if isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599:
            return value
    return None


def _provider_error_code(error: Exception) -> str | None:
    direct_code = _safe_log_identifier(getattr(error, "code", None))
    if direct_code is not None:
        return direct_code
    body = getattr(error, "body", None)
    if not isinstance(body, Mapping):
        return None
    body_mapping = cast(Mapping[object, object], body)
    nested_error = body_mapping.get("error")
    if isinstance(nested_error, Mapping):
        return _safe_log_identifier(cast(Mapping[object, object], nested_error).get("code"))
    return _safe_log_identifier(body_mapping.get("code"))


def _provider_request_id(error: Exception) -> str | None:
    direct = _safe_log_identifier(getattr(error, "request_id", None))
    if direct is not None:
        return direct
    headers = getattr(getattr(error, "response", None), "headers", None)
    get_header = getattr(headers, "get", None)
    if not callable(get_header):
        return None
    for header_name in ("x-request-id", "apim-request-id", "x-ms-request-id"):
        request_id = _safe_log_identifier(get_header(header_name))
        if request_id is not None:
            return request_id
    return None


def _safe_log_identifier(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > _MAX_LOG_IDENTIFIER_LENGTH:
        return None
    if not all(character.isalnum() or character in "._:-" for character in normalized):
        return None
    return normalized


def _provider_debug_body(value: object) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    projected = _redacted_debug_value(value, depth=0)
    serialized = json.dumps(projected, ensure_ascii=False, separators=(",", ":"), default=str)
    return _bounded_debug_text(serialized)


def _redacted_debug_value(value: object, *, depth: int) -> object:
    if depth >= _MAX_PROVIDER_DEBUG_DEPTH:
        return "<max-depth>"
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for index, (key, item) in enumerate(cast(Mapping[object, object], value).items()):
            if index >= _MAX_PROVIDER_DEBUG_ITEMS:
                result["<truncated-items>"] = True
                break
            name = str(key)
            if name.casefold() in _SENSITIVE_DEBUG_KEYS:
                result[name] = _REDACTED
            else:
                result[name] = _redacted_debug_value(item, depth=depth + 1)
        return result
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        items = cast(Sequence[object], value)
        projected = [
            _redacted_debug_value(item, depth=depth + 1)
            for item in items[:_MAX_PROVIDER_DEBUG_ITEMS]
        ]
        if len(items) > _MAX_PROVIDER_DEBUG_ITEMS:
            projected.append("<truncated-items>")
        return projected
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _bounded_debug_text(value: str) -> tuple[str, bool]:
    if len(value) <= _MAX_PROVIDER_DEBUG_CHARS:
        return value, False
    return value[:_MAX_PROVIDER_DEBUG_CHARS], True


def _exception_type(error: BaseException) -> str:
    error_type = type(error)
    return f"{error_type.__module__}.{error_type.__qualname__}"


def _exception_chain_types(error: BaseException) -> tuple[str, ...]:
    result: list[str] = []
    current: BaseException | None = error
    while current is not None and len(result) < 5:
        result.append(_exception_type(current))
        current = current.__cause__ or current.__context__
    return tuple(result)


def _safe_exc_info(
    error: Exception,
) -> tuple[type[RuntimeError], RuntimeError, TracebackType | None]:
    return RuntimeError, RuntimeError(_exception_type(error)), error.__traceback__
