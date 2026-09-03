"""Exact Context Resolver provider-request sizing and deterministic preflight splitting."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace

from docmind_llmmagic.application.pipeline.steps.document_context_resolver import (
    model_contract_limits,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelRequest,
)
from docmind_llmmagic.domain.pipeline.context_resolution import ContextAttributeSpec
from docmind_llmmagic.infrastructure.pipeline.context_resolver.payload import (
    request_data,
    serialize_provider_data,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.prompt import ContextResolverPrompt
from docmind_llmmagic.infrastructure.pipeline.context_resolver.structured_output import (
    context_resolver_response_format,
)


@dataclass(frozen=True, slots=True)
class ProviderRequestSizes:
    """Content-free byte counts for one exact provider call."""

    system_prompt_bytes: int
    user_data_bytes: int
    response_schema_bytes: int
    full_request_bytes: int

    def metadata(self) -> dict[str, int]:
        """Return stable safe fields for logs and Langfuse."""

        return {
            "system_prompt_bytes": self.system_prompt_bytes,
            "user_data_bytes": self.user_data_bytes,
            "response_schema_bytes": self.response_schema_bytes,
            "full_request_bytes": self.full_request_bytes,
        }


@dataclass(frozen=True, slots=True)
class PreparedProviderRequest:
    """The exact data, contract, call arguments, and sizes for one provider invocation."""

    data: dict[str, object]
    messages: tuple[dict[str, str], ...]
    response_format: Mapping[str, object]
    create_kwargs: dict[str, object]
    sizes: ProviderRequestSizes


def prepare_provider_request(
    request: ContextResolverModelRequest,
    *,
    prompt: ContextResolverPrompt,
    model_id: str,
    request_timeout_seconds: float,
) -> PreparedProviderRequest:
    """Build and measure the exact keyword arguments passed to the OpenAI SDK."""

    data = request_data(request)
    user_payload = serialize_provider_data(data)
    messages = (
        {"role": "system", "content": prompt.text},
        {"role": "user", "content": user_payload},
    )
    response_format = context_resolver_response_format(
        expected_attribute_ids=tuple(
            attribute.attribute_external_id for attribute in request.attributes
        ),
        evidence_ids=tuple(unit.evidence_id for unit in request.evidence),
    )
    create_kwargs: dict[str, object] = {
        "model": model_id,
        "messages": messages,
        "response_format": response_format,
        "max_completion_tokens": request.max_completion_tokens,
        "timeout": request_timeout_seconds,
    }
    if request.reasoning_effort is not None:
        create_kwargs["reasoning_effort"] = request.reasoning_effort
    return PreparedProviderRequest(
        data=data,
        messages=messages,
        response_format=response_format,
        create_kwargs=create_kwargs,
        sizes=ProviderRequestSizes(
            system_prompt_bytes=_utf8_bytes(prompt.text),
            user_data_bytes=_utf8_bytes(user_payload),
            response_schema_bytes=_json_bytes(response_format),
            full_request_bytes=_json_bytes(create_kwargs),
        ),
    )


def split_request_to_budget(
    request: ContextResolverModelRequest,
    *,
    prompt: ContextResolverPrompt,
    model_id: str,
    request_timeout_seconds: float,
    max_request_bytes: int,
) -> tuple[ContextResolverModelRequest, ...]:
    """Split contiguous attribute groups before any provider call when the request is large."""

    if not model_contract_limits.evidence_enum_within_limits(
        tuple(unit.evidence_id for unit in request.evidence)
    ):
        _raise_too_large()

    prepared = prepare_provider_request(
        request,
        prompt=prompt,
        model_id=model_id,
        request_timeout_seconds=request_timeout_seconds,
    )
    if prepared.sizes.full_request_bytes <= max_request_bytes:
        return (request,)

    groups: list[tuple[ContextAttributeSpec, ...]] = []
    current: tuple[ContextAttributeSpec, ...] = ()
    for attribute in request.attributes:
        candidate = (*current, attribute)
        candidate_request = replace(request, attributes=candidate)
        candidate_size = prepare_provider_request(
            candidate_request,
            prompt=prompt,
            model_id=model_id,
            request_timeout_seconds=request_timeout_seconds,
        ).sizes.full_request_bytes
        if candidate_size <= max_request_bytes:
            current = candidate
            continue
        if not current:
            _raise_too_large()
        groups.append(current)
        current = (attribute,)
        single_size = prepare_provider_request(
            replace(request, attributes=current),
            prompt=prompt,
            model_id=model_id,
            request_timeout_seconds=request_timeout_seconds,
        ).sizes.full_request_bytes
        if single_size > max_request_bytes:
            _raise_too_large()
    if current:
        groups.append(current)

    part_count = len(groups)
    return tuple(
        replace(
            request,
            batch_id=f"{request.batch_id}.part-{index:03d}-of-{part_count:03d}",
            attributes=group,
        )
        for index, group in enumerate(groups, start=1)
    )


def _raise_too_large() -> None:
    raise safe_context_resolver_error(
        code="CONTEXT_RESOLVER_INPUT_TOO_LARGE",
        message="Context Resolver provider request exceeds the supported safe limit.",
    )


def _json_bytes(value: object) -> int:
    return _utf8_bytes(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _utf8_bytes(value: str) -> int:
    return len(value.encode("utf-8"))
