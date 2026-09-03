"""OpenAI-backed adapter for one bounded Context Resolver batch."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Sequence
from dataclasses import replace
from time import perf_counter

from docmind_llmmagic.application.pipeline.observability import (
    BestEffortPipelineObserver,
    ModelIdentity,
    ModelIdentityRegistry,
    NoopPipelineObserver,
    ObservationType,
    PipelineObserver,
    TraceCaptureMode,
)
from docmind_llmmagic.application.pipeline.steps.document_agentic_context_resolver import (
    AgenticModelRequest,
    AgenticModelTurn,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    model_call_error,
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelRequest,
    ContextResolverModelResult,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.infrastructure.pipeline.agentic_context_resolver.openai_turns import (
    execute_agentic_turn,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.observation import (
    update_failed_observation,
    update_succeeded_observation,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.prompt import (
    DEFAULT_CONTEXT_RESOLVER_PROMPT_VERSION,
    context_resolver_prompt,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.provider_completion import (
    OpenAIClient,
    bounded_response_content,
    create_chat_completion,
    validate_completion_state,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.provider_errors import (
    provider_request_error,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.request_preflight import (
    PreparedProviderRequest,
    prepare_provider_request,
    split_request_to_budget,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.response_mapping import (
    model_result_from_payload,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.telemetry import (
    ModelResponseMetadata,
    ModelUsage,
    log_model_preflight_rejected,
    log_model_request_completed,
    log_model_request_failure,
    log_model_request_started,
    model_trace_metadata,
    model_usage,
    response_metadata,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.trace_projection import (
    generation_name,
    model_trace_input,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.validation_diagnostics import (
    model_output_validation_reason,
)


class OpenAIContextResolverClient:
    """Extract one exact bounded batch through an OpenAI chat completion."""

    def __init__(
        self,
        *,
        client: OpenAIClient,
        default_model_id: str,
        request_timeout_seconds: float,
        max_request_bytes: int = 120_000,
        prompt_version: str = DEFAULT_CONTEXT_RESOLVER_PROMPT_VERSION,
        trace_capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
        model_identity: ModelIdentity | None = None,
        model_identities: Sequence[ModelIdentity] = (),
        model_tracer: PipelineObserver | None = None,
        resources: tuple[object, ...] = (),
    ) -> None:
        self._client = client
        self._default_model_id = default_model_id
        self._request_timeout_seconds = request_timeout_seconds
        if max_request_bytes <= 0:
            raise ValueError("max_request_bytes must be positive")
        self._max_request_bytes = max_request_bytes
        self._prompt = context_resolver_prompt(prompt_version)
        self._trace_capture_mode = trace_capture_mode
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
        model_id = request.model_id or self._default_model_id
        model_identity = self._model_identities.resolve(model_id)
        original = prepare_provider_request(
            request,
            prompt=self._prompt,
            model_id=model_id,
            request_timeout_seconds=self._request_timeout_seconds,
        )
        try:
            requests = split_request_to_budget(
                request,
                prompt=self._prompt,
                model_id=model_id,
                request_timeout_seconds=self._request_timeout_seconds,
                max_request_bytes=self._max_request_bytes,
            )
        except PipelineStepError as error:
            request_shape = self._request_shape(
                original,
                split_index=0,
                split_count=0,
                original_full_request_bytes=original.sizes.full_request_bytes,
            )
            log_model_preflight_rejected(
                error=error,
                request=request,
                model_id=model_id,
                request_timeout_seconds=self._request_timeout_seconds,
                request_shape=request_shape,
            )
            raise model_call_error(error, provider_request_count=0) from error

        results: list[ContextResolverModelResult] = []
        for index, split_request in enumerate(requests, start=1):
            prepared = prepare_provider_request(
                split_request,
                prompt=self._prompt,
                model_id=model_id,
                request_timeout_seconds=self._request_timeout_seconds,
            )
            try:
                result = await self._resolve_prepared(
                    split_request,
                    prepared=prepared,
                    model_id=model_id,
                    model_identity=model_identity,
                    request_shape=self._request_shape(
                        prepared,
                        split_index=index,
                        split_count=len(requests),
                        original_full_request_bytes=original.sizes.full_request_bytes,
                    ),
                )
            except PipelineStepError as error:
                raise model_call_error(error, provider_request_count=index) from error
            results.append(result)
        return ContextResolverModelResult(
            attributes=tuple(attribute for result in results for attribute in result.attributes),
            provider_request_count=len(results),
        )

    async def agentic_turn(self, request: AgenticModelRequest) -> AgenticModelTurn:
        """Execute one preflight-bounded complete-document turn for Agentic CR."""

        model_id = request.model_id or self._default_model_id
        return await execute_agentic_turn(
            client=self._client,
            request=request,
            default_model_id=self._default_model_id,
            max_request_bytes=self._max_request_bytes,
            trace_capture_mode=self._trace_capture_mode,
            model_identity=self._model_identities.resolve(model_id),
            model_tracer=self._model_tracer,
        )

    async def _resolve_prepared(
        self,
        request: ContextResolverModelRequest,
        *,
        prepared: PreparedProviderRequest,
        model_id: str,
        model_identity: ModelIdentity,
        request_shape: dict[str, object],
    ) -> ContextResolverModelResult:
        """Execute and trace one preflight-approved provider request."""

        started_at = perf_counter()
        usage: ModelUsage | None = None
        metadata: ModelResponseMetadata | None = None
        response_content: str | None = None
        validation_reason: str | None = None

        log_model_request_started(
            request=request,
            model_id=model_id,
            request_timeout_seconds=self._request_timeout_seconds,
            request_shape=request_shape,
        )
        try:
            with self._model_tracer.observe(
                observation_type=ObservationType.GENERATION,
                name=generation_name(request.repair_kind),
                model=model_identity.langfuse_model_id,
                user_id=request.user_id,
                session_id=request.run_id or request.session_id,
                input_data=model_trace_input(
                    request,
                    prompt=self._prompt,
                    data=prepared.data,
                    response_format=prepared.response_format,
                    model_id=model_id,
                    request_timeout_seconds=self._request_timeout_seconds,
                    capture_mode=self._trace_capture_mode,
                    request_shape=request_shape,
                ),
                metadata={
                    **model_trace_metadata(request),
                    **model_identity.metadata(),
                    "prompt_version": self._prompt.version,
                    "prompt_sha256": self._prompt.sha256,
                    "capture_mode": self._trace_capture_mode.value,
                },
            ) as observation:
                try:
                    response = await create_chat_completion(
                        self._client,
                        create_kwargs=prepared.create_kwargs,
                    )
                    usage = model_usage(response)
                    metadata = response_metadata(response)
                    validate_completion_state(metadata)
                    response_content = bounded_response_content(response)
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
                    validation_reason = model_output_validation_reason(exc)
                    error = safe_context_resolver_error(
                        code="CONTEXT_RESOLVER_MODEL_OUTPUT_INVALID",
                        message="Context Resolver model output is invalid.",
                    )
                    update_failed_observation(
                        observation,
                        request=request,
                        metadata=metadata,
                        usage=usage,
                        raw_response=response_content,
                        model_identity=model_identity,
                        prompt=self._prompt,
                        capture_mode=self._trace_capture_mode,
                        latency_seconds=perf_counter() - started_at,
                        error=error,
                        request_shape=request_shape,
                        validation_reason=validation_reason,
                    )
                    raise error from exc
                except Exception as exc:
                    update_failed_observation(
                        observation,
                        request=request,
                        metadata=metadata,
                        usage=usage,
                        raw_response=response_content,
                        model_identity=model_identity,
                        prompt=self._prompt,
                        capture_mode=self._trace_capture_mode,
                        latency_seconds=perf_counter() - started_at,
                        error=exc,
                        request_shape=request_shape,
                    )
                    raise
                update_succeeded_observation(
                    observation,
                    request=request,
                    result=result,
                    raw_response=response_content,
                    metadata=metadata,
                    usage=usage,
                    model_identity=model_identity,
                    prompt=self._prompt,
                    capture_mode=self._trace_capture_mode,
                    latency_seconds=perf_counter() - started_at,
                    request_shape=request_shape,
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
                request_shape=request_shape,
                validation_reason=validation_reason,
            )
            raise
        except Exception as exc:
            error = provider_request_error(exc)
            log_model_request_failure(
                error=exc,
                error_code=error.code,
                request=request,
                model_id=model_id,
                request_timeout_seconds=self._request_timeout_seconds,
                latency_seconds=perf_counter() - started_at,
                metadata=metadata,
                usage=usage,
                request_shape=request_shape,
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
            request_shape=request_shape,
        )
        return result

    def _request_shape(
        self,
        prepared: PreparedProviderRequest,
        *,
        split_index: int,
        split_count: int,
        original_full_request_bytes: int,
    ) -> dict[str, object]:
        return {
            **prepared.sizes.metadata(),
            "max_request_bytes": self._max_request_bytes,
            "preflight_split_index": split_index,
            "preflight_split_count": split_count,
            "original_full_request_bytes": original_full_request_bytes,
        }
