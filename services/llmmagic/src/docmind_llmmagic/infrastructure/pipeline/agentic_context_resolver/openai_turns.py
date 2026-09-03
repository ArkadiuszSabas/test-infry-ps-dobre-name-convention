"""Bounded quote-grounded OpenAI turn with exact request preflight."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import replace
from time import perf_counter
from typing import cast

from docmind_llmmagic.application.pipeline.observability import (
    BestEffortPipelineObserver,
    ModelIdentity,
    NoopPipelineObserver,
    ObservationType,
    PipelineObserver,
    TraceCaptureMode,
)
from docmind_llmmagic.application.pipeline.steps.document_agentic_context_resolver import (
    constants as agentic_constants,
)
from docmind_llmmagic.application.pipeline.steps.document_agentic_context_resolver.ports import (
    AgenticAttributeResult,
    AgenticCandidate,
    AgenticModelRequest,
    AgenticModelTurn,
    AgenticQuote,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.infrastructure.pipeline.agentic_context_resolver.observation import (
    agentic_trace_input,
    agentic_trace_metadata,
    update_agentic_failed_observation,
    update_agentic_succeeded_observation,
)
from docmind_llmmagic.infrastructure.pipeline.agentic_context_resolver.provider_contract import (
    provider_messages,
    provider_response_format,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.provider_completion import (
    OpenAIClient,
    bounded_response_content,
    create_chat_completion,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.provider_errors import (
    provider_request_error,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.telemetry import (
    ModelUsage,
    model_usage,
    response_metadata,
)


async def execute_agentic_turn(
    *,
    client: OpenAIClient,
    request: AgenticModelRequest,
    default_model_id: str,
    max_request_bytes: int,
    trace_capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
    model_identity: ModelIdentity | None = None,
    model_tracer: PipelineObserver | None = None,
) -> AgenticModelTurn:
    """Preflight complete create kwargs and split oversized views only on page boundaries."""

    requests = _preflight_requests(
        request,
        default_model_id=default_model_id,
        max_request_bytes=max_request_bytes,
    )
    turns: list[AgenticModelTurn] = []
    for item in requests:
        turn = await _execute_single_turn(
            client=client,
            request=item,
            default_model_id=default_model_id,
            trace_capture_mode=trace_capture_mode,
            model_identity=model_identity,
            model_tracer=model_tracer,
        )
        turns.append(turn)
        if turn.output_error_code is not None:
            break
    return _merge_turns(turns, expected_handles=tuple(target.handle for target in request.targets))


def _preflight_requests(
    request: AgenticModelRequest,
    *,
    default_model_id: str,
    max_request_bytes: int,
) -> tuple[AgenticModelRequest, ...]:
    if (
        serialized_request_bytes(
            agentic_create_kwargs(
                request,
                default_model_id=default_model_id,
            )
        )
        <= max_request_bytes
    ):
        return (request,)
    if not request.document_view.pages:
        raise _request_too_large()

    partitions: list[AgenticModelRequest] = []
    current_pages: tuple[int, ...] = ()
    for page in request.document_view.pages:
        candidate_pages = (*current_pages, page.page_number)
        candidate = replace(
            request,
            document_view=request.document_view.for_pages(candidate_pages),
        )
        candidate_bytes = serialized_request_bytes(
            agentic_create_kwargs(
                candidate,
                default_model_id=default_model_id,
            )
        )
        if candidate_bytes <= max_request_bytes:
            current_pages = candidate_pages
            continue
        if not current_pages:
            raise _request_too_large()
        partitions.append(
            replace(request, document_view=request.document_view.for_pages(current_pages))
        )
        current_pages = (page.page_number,)
        single = replace(
            request,
            document_view=request.document_view.for_pages(current_pages),
        )
        if (
            serialized_request_bytes(
                agentic_create_kwargs(
                    single,
                    default_model_id=default_model_id,
                )
            )
            > max_request_bytes
        ):
            raise _request_too_large()
    if current_pages:
        partitions.append(
            replace(request, document_view=request.document_view.for_pages(current_pages))
        )
    return tuple(partitions)


async def _execute_single_turn(
    *,
    client: OpenAIClient,
    request: AgenticModelRequest,
    default_model_id: str,
    trace_capture_mode: TraceCaptureMode,
    model_identity: ModelIdentity | None,
    model_tracer: PipelineObserver | None,
) -> AgenticModelTurn:
    handles = tuple(target.handle for target in request.targets)
    model_id = request.model_id or default_model_id
    identity = model_identity or ModelIdentity(
        provider_id="openai",
        deployment_name=model_id,
        canonical_model_id=model_id,
    )
    tracer = (
        BestEffortPipelineObserver(model_tracer)
        if model_tracer is not None
        else NoopPipelineObserver()
    )
    kwargs = agentic_create_kwargs(
        request,
        default_model_id=default_model_id,
    )
    request_bytes = serialized_request_bytes(kwargs)
    started_at = perf_counter()
    usage: ModelUsage | None = None
    raw_response: str | None = None
    with tracer.observe(
        observation_type=ObservationType.GENERATION,
        name="agentic-context-resolver.turn",
        model=identity.langfuse_model_id,
        user_id=request.user_id,
        session_id=request.run_id,
        input_data=agentic_trace_input(
            request,
            create_kwargs=kwargs,
            capture_mode=trace_capture_mode,
            request_bytes=request_bytes,
        ),
        metadata=agentic_trace_metadata(
            request,
            model_identity=identity,
            capture_mode=trace_capture_mode,
            request_bytes=request_bytes,
            status="started",
        ),
    ) as observation:
        try:
            response = await create_chat_completion(client, create_kwargs=kwargs)
            usage = model_usage(response)
        except PipelineStepError as exc:
            update_agentic_failed_observation(
                observation,
                request=request,
                model_identity=identity,
                capture_mode=trace_capture_mode,
                request_bytes=request_bytes,
                latency_seconds=perf_counter() - started_at,
                error=exc,
                usage=usage,
                raw_response=raw_response,
                error_code=exc.code,
            )
            raise
        except Exception as exc:
            error = provider_request_error(exc)
            update_agentic_failed_observation(
                observation,
                request=request,
                model_identity=identity,
                capture_mode=trace_capture_mode,
                request_bytes=request_bytes,
                latency_seconds=perf_counter() - started_at,
                error=exc,
                usage=usage,
                raw_response=raw_response,
                error_code=error.code,
            )
            raise error from exc

        input_tokens = 0
        output_tokens = 0
        finish_reason: str | None = None
        try:
            _first_message(response)
            input_tokens, output_tokens = _token_usage(response)
            completion_metadata = response_metadata(response)
            finish_reason = completion_metadata.finish_reason
            if finish_reason == "length":
                turn = AgenticModelTurn(
                    input_token_count=input_tokens,
                    output_token_count=output_tokens,
                    output_error_code="MODEL_OUTPUT_TRUNCATED",
                    finish_reason=finish_reason,
                    truncated_response_count=1,
                )
            elif (
                completion_metadata.refusal
                or completion_metadata.incomplete
                or (finish_reason is not None and finish_reason != "stop")
            ):
                turn = AgenticModelTurn(
                    input_token_count=input_tokens,
                    output_token_count=output_tokens,
                    output_error_code="MODEL_OUTPUT_INCOMPLETE",
                    finish_reason=finish_reason,
                )
            else:
                raw_response = bounded_response_content(response)
                payload = cast(object, json.loads(raw_response))
                turn = AgenticModelTurn(
                    results=_results(payload, expected_handles=handles),
                    input_token_count=input_tokens,
                    output_token_count=output_tokens,
                    finish_reason=finish_reason,
                )
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            turn = AgenticModelTurn(
                output_error_code=_output_error_code(exc),
                input_token_count=input_tokens,
                output_token_count=output_tokens,
                finish_reason=finish_reason,
            )
        update_agentic_succeeded_observation(
            observation,
            request=request,
            turn=turn,
            model_identity=identity,
            capture_mode=trace_capture_mode,
            request_bytes=request_bytes,
            latency_seconds=perf_counter() - started_at,
            usage=usage,
            raw_response=raw_response,
        )
        return turn


def agentic_create_kwargs(
    request: AgenticModelRequest,
    *,
    default_model_id: str,
) -> dict[str, object]:
    return {
        "model": request.model_id or default_model_id,
        "messages": provider_messages(request),
        "response_format": provider_response_format(request),
        "max_completion_tokens": request.max_completion_tokens,
        "timeout": agentic_constants.AGENTIC_REQUEST_TIMEOUT_SECONDS,
    }


def serialized_request_bytes(kwargs: Mapping[str, object]) -> int:
    return len(
        json.dumps(kwargs, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    )


def _request_too_large() -> PipelineStepError:
    return safe_context_resolver_error(
        code="AGENTIC_CONTEXT_RESOLVER_REQUEST_TOO_LARGE",
        message="Agentic Context Resolver request exceeds the provider limit.",
    )


def _merge_turns(
    turns: list[AgenticModelTurn],
    *,
    expected_handles: tuple[str, ...],
) -> AgenticModelTurn:
    provider_requests = sum(turn.provider_request_count for turn in turns)
    input_tokens = sum(turn.input_token_count for turn in turns)
    output_tokens = sum(turn.output_token_count for turn in turns)
    truncated_responses = sum(turn.truncated_response_count for turn in turns)
    finish_reason = _merged_finish_reason(turns)
    invalid = next((turn.output_error_code for turn in turns if turn.output_error_code), None)
    if invalid is not None:
        return AgenticModelTurn(
            provider_request_count=provider_requests,
            input_token_count=input_tokens,
            output_token_count=output_tokens,
            output_error_code=invalid,
            finish_reason=finish_reason,
            truncated_response_count=truncated_responses,
        )
    by_handle = {
        handle: [result for turn in turns for result in turn.results if result.handle == handle]
        for handle in expected_handles
    }
    merged: list[AgenticAttributeResult] = []
    for handle in expected_handles:
        results = by_handle[handle]
        candidates = _merged_candidates(results)
        distinct_values = {candidate.value.casefold() for candidate in candidates}
        if not candidates:
            status = "missing"
        elif len(distinct_values) > 1 or any(result.status == "conflicting" for result in results):
            status = "conflicting"
        elif any(result.status == "uncertain" for result in results):
            status = "uncertain"
        else:
            status = "present"
        merged.append(
            AgenticAttributeResult(
                handle=handle,
                status=status,
                candidates=candidates,
                selected_candidate=0 if candidates else None,
            )
        )
    return AgenticModelTurn(
        results=tuple(merged),
        provider_request_count=provider_requests,
        input_token_count=input_tokens,
        output_token_count=output_tokens,
        finish_reason=finish_reason,
        truncated_response_count=truncated_responses,
    )


def _merged_candidates(
    results: list[AgenticAttributeResult],
) -> tuple[AgenticCandidate, ...]:
    by_value: dict[str, list[AgenticCandidate]] = {}
    for result in results:
        for candidate in result.candidates:
            key = " ".join(candidate.value.split()).casefold()
            by_value.setdefault(key, []).append(candidate)
    merged: list[AgenticCandidate] = []
    for candidates in by_value.values():
        selected = max(candidates, key=lambda item: item.confidence)
        merged.append(selected)
    return tuple(sorted(merged, key=lambda item: item.confidence, reverse=True))


def _merged_finish_reason(turns: list[AgenticModelTurn]) -> str | None:
    reasons = tuple(turn.finish_reason for turn in turns if turn.finish_reason is not None)
    return next(
        (reason for reason in reversed(reasons) if reason != "stop"),
        reasons[-1] if reasons else None,
    )


def _first_message(response: object) -> object:
    choices = getattr(response, "choices", ())
    if not isinstance(choices, Sequence) or not choices:
        raise ValueError("missing response choice")
    return getattr(cast(Sequence[object], choices)[0], "message", None)


def _results(
    payload: object,
    *,
    expected_handles: tuple[str, ...],
) -> tuple[AgenticAttributeResult, ...]:
    envelope = _string_mapping(payload)
    if set(envelope) != {"results"}:
        raise ValueError("invalid result envelope")
    result_items = _string_mapping(envelope["results"])
    if set(result_items) != set(expected_handles):
        raise ValueError("invalid result handle set")
    results: list[AgenticAttributeResult] = []
    for handle in expected_handles:
        result_mapping = _string_mapping(result_items[handle])
        if set(result_mapping) != {"status", "candidates"}:
            raise ValueError("invalid result")
        raw_candidates = result_mapping["candidates"]
        status = result_mapping["status"]
        if not isinstance(raw_candidates, list):
            raise ValueError("invalid candidates")
        if not isinstance(status, str):
            raise ValueError("invalid result strings")
        candidates = tuple(_candidate(item) for item in cast(list[object], raw_candidates))
        results.append(
            AgenticAttributeResult(
                handle=handle,
                status=status,
                candidates=candidates,
                selected_candidate=0 if candidates and status != "missing" else None,
            )
        )
    return tuple(results)


def _candidate(value: object) -> AgenticCandidate:
    mapping = _string_mapping(value)
    if set(mapping) != {"value", "derivation", "confidence", "evidence"}:
        raise ValueError("invalid candidate")
    candidate_value = mapping["value"]
    derivation = mapping["derivation"]
    confidence = mapping["confidence"]
    raw_evidence = mapping["evidence"]
    if (
        not isinstance(candidate_value, str)
        or not isinstance(derivation, str)
        or not isinstance(confidence, int | float)
        or isinstance(confidence, bool)
        or not 0 <= confidence <= 1
        or not isinstance(raw_evidence, list)
    ):
        raise ValueError("invalid candidate fields")
    return AgenticCandidate(
        value=candidate_value,
        derivation=derivation,
        confidence=float(confidence),
        evidence=tuple(_quote(item) for item in cast(list[object], raw_evidence)),
    )


def _quote(value: object) -> AgenticQuote:
    mapping = _string_mapping(value)
    if set(mapping) != {"quote", "page"}:
        raise ValueError("invalid evidence quote")
    quote = mapping["quote"]
    page = mapping["page"]
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError("invalid evidence quote")
    if page is not None and (not isinstance(page, int) or isinstance(page, bool) or page < 1):
        raise ValueError("invalid evidence page")
    return AgenticQuote(quote=quote, page=page)


def _string_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("object is required")
    mapping = cast(Mapping[object, object], value)
    if any(not isinstance(key, str) for key in mapping):
        raise ValueError("object keys must be strings")
    return {cast(str, key): item for key, item in mapping.items()}


def _token_usage(response: object) -> tuple[int, int]:
    usage = cast(object, getattr(response, "usage", None))
    input_tokens = cast(object, getattr(usage, "prompt_tokens", 0))
    output_tokens = cast(object, getattr(usage, "completion_tokens", 0))
    return (
        input_tokens if isinstance(input_tokens, int) and input_tokens >= 0 else 0,
        output_tokens if isinstance(output_tokens, int) and output_tokens >= 0 else 0,
    )


def _output_error_code(error: Exception) -> str:
    if isinstance(error, json.JSONDecodeError):
        return "MODEL_OUTPUT_JSON_INVALID"
    return {
        "invalid candidate": "MODEL_OUTPUT_CANDIDATE_INVALID",
        "invalid candidate fields": "MODEL_OUTPUT_CANDIDATE_FIELDS_INVALID",
        "invalid candidates": "MODEL_OUTPUT_CANDIDATES_INVALID",
        "invalid evidence page": "MODEL_OUTPUT_EVIDENCE_PAGE_INVALID",
        "invalid evidence quote": "MODEL_OUTPUT_EVIDENCE_QUOTE_INVALID",
        "invalid result": "MODEL_OUTPUT_RESULT_INVALID",
        "invalid result envelope": "MODEL_OUTPUT_ENVELOPE_INVALID",
        "invalid result handle set": "MODEL_OUTPUT_HANDLE_SET_INVALID",
        "invalid result strings": "MODEL_OUTPUT_RESULT_FIELDS_INVALID",
    }.get(str(error), "MODEL_OUTPUT_CONTRACT_INVALID")
