"""OpenAI-backed adapter for one bounded Context Resolver batch."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Mapping, Sequence
from dataclasses import replace
from importlib import import_module
from time import perf_counter
from typing import Any, Protocol, cast

from docmind_llmmagic.application.pipeline.observability import (
    BestEffortPipelineObserver,
    ModelIdentity,
    ModelIdentityRegistry,
    NoopPipelineObserver,
    ObservationType,
    PipelineObserver,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelRequest,
    ContextResolverModelResult,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.infrastructure.pipeline.context_resolver.payload import request_payload
from docmind_llmmagic.infrastructure.pipeline.context_resolver.prompt import (
    CONTEXT_RESOLVER_PROMPT_SHA256,
    CONTEXT_RESOLVER_PROMPT_VERSION,
    CONTEXT_RESOLVER_SYSTEM_PROMPT,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.response_mapping import (
    model_result_from_payload,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.structured_output import (
    context_resolver_response_format,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.telemetry import (
    ModelResponseMetadata,
    ModelUsage,
    log_model_request_completed,
    log_model_request_failure,
    log_model_request_started,
    model_trace_input,
    model_trace_metadata,
    model_usage,
    response_metadata,
)

_MAX_MODEL_RESPONSE_CHARS = 100_000


class _ChatCompletions(Protocol):
    async def create(self, **kwargs: object) -> object: ...


class _ChatResource(Protocol):
    completions: _ChatCompletions


class _OpenAIClient(Protocol):
    chat: _ChatResource


class OpenAIContextResolverClient:
    """Extract one exact bounded batch through an OpenAI chat completion."""

    def __init__(
        self,
        *,
        client: _OpenAIClient,
        default_model_id: str,
        request_timeout_seconds: float,
        model_identity: ModelIdentity | None = None,
        model_identities: Sequence[ModelIdentity] = (),
        model_tracer: PipelineObserver | None = None,
        resources: tuple[object, ...] = (),
    ) -> None:
        self._client = client
        self._default_model_id = default_model_id
        self._request_timeout_seconds = request_timeout_seconds
        default_identity = model_identity or ModelIdentity(
            provider_id="openai",
            deployment_name=default_model_id,
            canonical_model_id=default_model_id,
        )
        additional_identities = tuple(
            identity
            for identity in model_identities
            if identity.deployment_name != default_identity.deployment_name
        )
        self._model_identities = ModelIdentityRegistry.from_identities(
            (default_identity, *additional_identities),
            fallback_provider_id=default_identity.provider_id,
        )
        self._model_tracer = (
            BestEffortPipelineObserver(model_tracer)
            if model_tracer is not None
            else NoopPipelineObserver()
        )
        self._resources = resources

    async def close(self) -> None:
        """Release the OpenAI transport and app-scoped resources."""

        close = getattr(self._client, "close", None) or getattr(self._client, "aclose", None)
        if callable(close):
            result = close()
            if isinstance(result, Awaitable):
                await result
        for resource in self._resources:
            resource_close = getattr(resource, "close", None)
            if callable(resource_close):
                result = resource_close()
                if isinstance(result, Awaitable):
                    await result

    async def resolve_attributes(
        self,
        request: ContextResolverModelRequest,
    ) -> ContextResolverModelResult:
        """Extract and validate every exact attribute key in one batch."""

        if request.model_id is not None and request.model_id != self._default_model_id:
            request = replace(request, reasoning_effort=None)
        user_payload = request_payload(request)
        model_id = request.model_id or self._default_model_id
        model_identity = self._model_identities.resolve(model_id)
        messages = (
            {"role": "system", "content": CONTEXT_RESOLVER_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        )
        response_format = context_resolver_response_format(
            expected_attribute_ids=tuple(
                attribute.attribute_external_id for attribute in request.attributes
            ),
            evidence_ids=tuple(unit.evidence_id for unit in request.evidence),
        )
        started_at = perf_counter()
        usage: ModelUsage | None = None
        metadata: ModelResponseMetadata | None = None
        response_content: str | None = None

        log_model_request_started(
            request=request,
            model_id=model_id,
            request_timeout_seconds=self._request_timeout_seconds,
        )
        try:
            with self._model_tracer.observe(
                observation_type=ObservationType.GENERATION,
                name=_generation_name(request.repair_kind),
                model=model_identity.langfuse_model_id,
                user_id=request.user_id,
                session_id=request.run_id or request.session_id,
                input_data=model_trace_input(
                    request,
                    messages=messages,
                    response_format=response_format,
                    model_id=model_id,
                    request_timeout_seconds=self._request_timeout_seconds,
                ),
                metadata={
                    **model_trace_metadata(request),
                    **model_identity.metadata(),
                    "prompt_version": CONTEXT_RESOLVER_PROMPT_VERSION,
                    "prompt_sha256": CONTEXT_RESOLVER_PROMPT_SHA256,
                },
            ) as observation:
                try:
                    response = await _create_chat_completion(
                        self._client,
                        request=request,
                        model_id=model_id,
                        messages=messages,
                        response_format=response_format,
                        request_timeout_seconds=self._request_timeout_seconds,
                    )
                    usage = model_usage(response)
                    metadata = response_metadata(response)
                    _validate_completion_state(metadata)
                    response_content = _bounded_response_content(response)
                    result = model_result_from_payload(
                        json.loads(response_content),
                        expected_attribute_ids=tuple(
                            attribute.attribute_external_id for attribute in request.attributes
                        ),
                        allowed_evidence_ids=frozenset(
                            unit.evidence_id for unit in request.evidence
                        ),
                    )
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    _update_failed_observation(
                        observation,
                        request=request,
                        metadata=metadata,
                        usage=usage,
                        raw_response=response_content,
                        model_identity=model_identity,
                    )
                    raise safe_context_resolver_error(
                        code="CONTEXT_RESOLVER_MODEL_OUTPUT_INVALID",
                        message="Context Resolver model output is invalid.",
                    ) from exc
                except Exception:
                    _update_failed_observation(
                        observation,
                        request=request,
                        metadata=metadata,
                        usage=usage,
                        raw_response=response_content,
                        model_identity=model_identity,
                    )
                    raise
                _update_succeeded_observation(
                    observation,
                    request=request,
                    result=result,
                    raw_response=response_content,
                    metadata=metadata,
                    usage=usage,
                    model_identity=model_identity,
                )
        except PipelineStepError as exc:
            log_model_request_failure(
                error=exc,
                error_code=exc.code,
                request=request,
                model_id=model_id,
                request_timeout_seconds=self._request_timeout_seconds,
                latency_seconds=perf_counter() - started_at,
                metadata=metadata,
                usage=usage,
            )
            raise
        except Exception as exc:
            error = _provider_request_error(exc)
            log_model_request_failure(
                error=exc,
                error_code=error.code,
                request=request,
                model_id=model_id,
                request_timeout_seconds=self._request_timeout_seconds,
                latency_seconds=perf_counter() - started_at,
                metadata=metadata,
                usage=usage,
            )
            raise error from exc

        log_model_request_completed(
            request=request,
            model_id=model_id,
            latency_seconds=perf_counter() - started_at,
            response_char_count=len(response_content),
            result_count=len(result.attributes),
            metadata=metadata,
            usage=usage,
        )
        return result


async def _create_chat_completion(
    client: _OpenAIClient,
    *,
    request: ContextResolverModelRequest,
    model_id: str,
    messages: tuple[dict[str, str], ...],
    response_format: Mapping[str, object],
    request_timeout_seconds: float,
) -> object:
    create_kwargs: dict[str, object] = {
        "model": model_id,
        "messages": messages,
        "response_format": response_format,
        "max_completion_tokens": request.max_completion_tokens,
        "timeout": request_timeout_seconds,
    }
    if request.reasoning_effort is not None:
        create_kwargs["reasoning_effort"] = request.reasoning_effort
    return await client.chat.completions.create(**create_kwargs)


def _validate_completion_state(metadata: ModelResponseMetadata) -> None:
    if metadata.refusal or metadata.incomplete or metadata.finish_reason != "stop":
        raise ValueError("model response did not complete successfully")


def _provider_request_error(exc: Exception) -> PipelineStepError:
    status_code = _provider_status_code(exc)
    if status_code == 400:
        code = "CONTEXT_RESOLVER_MODEL_REQUEST_REJECTED"
    elif status_code in {401, 403}:
        code = "CONTEXT_RESOLVER_MODEL_AUTH_FAILED"
    elif status_code == 404:
        code = "CONTEXT_RESOLVER_MODEL_NOT_FOUND"
    elif status_code == 408:
        code = "CONTEXT_RESOLVER_MODEL_TIMEOUT"
    elif status_code == 429:
        code = "CONTEXT_RESOLVER_MODEL_RATE_LIMITED"
    elif status_code is not None and status_code >= 500:
        code = "CONTEXT_RESOLVER_MODEL_UNAVAILABLE"
    else:
        code = "CONTEXT_RESOLVER_MODEL_REQUEST_FAILED"
    return safe_context_resolver_error(
        code=code,
        message="Context Resolver model request failed.",
    )


def _provider_status_code(exc: Exception) -> int | None:
    for value in (
        getattr(exc, "status_code", None),
        getattr(getattr(exc, "response", None), "status_code", None),
    ):
        if isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599:
            return value
    return None


def _response_content(response: object) -> str:
    choices = getattr(response, "choices", ())
    if isinstance(choices, Sequence) and choices:
        message = getattr(cast(Sequence[object], choices)[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str) and content:
            return content
    raise ValueError("missing response content")


def _bounded_response_content(response: object) -> str:
    content = _response_content(response)
    if len(content) > _MAX_MODEL_RESPONSE_CHARS:
        raise ValueError("response content exceeds safe limit")
    return content


def _update_failed_observation(
    observation: object,
    *,
    request: ContextResolverModelRequest,
    metadata: ModelResponseMetadata | None,
    usage: ModelUsage | None,
    raw_response: str | None,
    model_identity: ModelIdentity,
) -> None:
    update: dict[str, object] = {
        "metadata": {
            "status": "failed",
            **model_trace_metadata(request),
            **model_identity.metadata(),
            "prompt_version": CONTEXT_RESOLVER_PROMPT_VERSION,
            "prompt_sha256": CONTEXT_RESOLVER_PROMPT_SHA256,
        },
        "output": {
            "status": "failed",
            "finish_reason": metadata.finish_reason if metadata is not None else None,
            "refusal": metadata.refusal if metadata is not None else False,
            "incomplete": metadata.incomplete if metadata is not None else False,
            "exact_contract_validation": False,
            "raw_response": raw_response,
        },
        "level": "ERROR",
        "status_message": "Model request or response validation failed.",
    }
    usage_details = usage.langfuse_details() if usage is not None else None
    if usage_details is not None:
        update["usage_details"] = usage_details
    cast(Any, observation).update(**update)


def _update_succeeded_observation(
    observation: object,
    *,
    request: ContextResolverModelRequest,
    result: ContextResolverModelResult,
    raw_response: str,
    metadata: ModelResponseMetadata,
    usage: ModelUsage | None,
    model_identity: ModelIdentity,
) -> None:
    update: dict[str, object] = {
        "metadata": {
            "status": "succeeded",
            **model_trace_metadata(request),
            **model_identity.metadata(),
            "prompt_version": CONTEXT_RESOLVER_PROMPT_VERSION,
            "prompt_sha256": CONTEXT_RESOLVER_PROMPT_SHA256,
        },
        "output": {
            "status": "succeeded",
            "raw_response": raw_response,
            "parsed_response": {
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
            },
            "result_count": len(result.attributes),
            "response_char_count": len(raw_response),
            "finish_reason": metadata.finish_reason,
            "refusal": metadata.refusal,
            "incomplete": metadata.incomplete,
            "exact_contract_validation": True,
        },
    }
    usage_details = usage.langfuse_details() if usage is not None else None
    if usage_details is not None:
        update["usage_details"] = usage_details
    cast(Any, observation).update(**update)


def _generation_name(repair_kind: str) -> str:
    return {
        "technical_retry": "context-resolver.repair",
        "coverage_fallback": "context-resolver.coverage",
    }.get(repair_kind, "context-resolver.primary")


class UnconfiguredContextResolverModelClient:
    """Fail closed when the Context Resolver provider is not configured."""

    async def resolve_attributes(
        self,
        request: ContextResolverModelRequest,
    ) -> ContextResolverModelResult:
        del request
        raise safe_context_resolver_error(
            code="CONTEXT_RESOLVER_OPENAI_NOT_CONFIGURED",
            message="Context Resolver OpenAI provider is not configured.",
        )


def build_openai_context_resolver_client(
    *,
    default_model_id: str,
    request_timeout_seconds: float,
    base_url: str,
    managed_identity_client_id: str | None = None,
    model_tracer: PipelineObserver | None = None,
    model_identity: ModelIdentity | None = None,
    model_identities: Sequence[ModelIdentity] = (),
) -> OpenAIContextResolverClient:
    """Build an Azure AI Foundry OpenAI client with SDK retries disabled."""

    if not base_url:
        raise ValueError("Azure AI Foundry project endpoint is required.")
    credential = _build_foundry_credential(
        managed_identity_client_id=managed_identity_client_id,
    )
    project_module = import_module("azure.ai.projects.aio")
    project_client_class: Any = project_module.__dict__["AIProjectClient"]
    project_client = project_client_class(endpoint=base_url, credential=credential)
    client: _OpenAIClient = project_client.get_openai_client(
        timeout=request_timeout_seconds,
        max_retries=0,
    )
    return OpenAIContextResolverClient(
        client=client,
        default_model_id=default_model_id,
        request_timeout_seconds=request_timeout_seconds,
        model_tracer=model_tracer,
        model_identity=model_identity,
        model_identities=model_identities,
        resources=(
            project_client,
            credential,
        ),
    )


def _build_foundry_credential(*, managed_identity_client_id: str | None) -> object:
    identity_module = import_module("azure.identity.aio")
    if managed_identity_client_id:
        credential_class: Any = identity_module.__dict__["ManagedIdentityCredential"]
        return credential_class(client_id=managed_identity_client_id)
    credential_class = identity_module.__dict__["DefaultAzureCredential"]
    return credential_class()
