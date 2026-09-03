"""Deterministic attribute grouping by response shape and model-visible size."""

import json
from math import ceil

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError

from .config import AgenticAttributeSpec


def grouped_attributes(
    attributes: tuple[AgenticAttributeSpec, ...],
    *,
    max_attributes: int,
    max_request_bytes: int,
    max_estimated_output_tokens: int,
) -> tuple[tuple[AgenticAttributeSpec, ...], ...]:
    """Keep scalar and long-text outputs separate under all three group limits."""

    scalar = tuple(attribute for attribute in attributes if not _is_long_text(attribute))
    long_text = tuple(attribute for attribute in attributes if _is_long_text(attribute))
    return (
        *_group_bucket(
            scalar,
            max_attributes=max_attributes,
            max_request_bytes=max_request_bytes,
            max_estimated_output_tokens=max_estimated_output_tokens,
        ),
        *_group_bucket(
            long_text,
            max_attributes=max_attributes,
            max_request_bytes=max_request_bytes,
            max_estimated_output_tokens=max_estimated_output_tokens,
        ),
    )


def _group_bucket(
    attributes: tuple[AgenticAttributeSpec, ...],
    *,
    max_attributes: int,
    max_request_bytes: int,
    max_estimated_output_tokens: int,
) -> tuple[tuple[AgenticAttributeSpec, ...], ...]:
    """Group one output-shape bucket in stable configuration order."""

    groups: list[tuple[AgenticAttributeSpec, ...]] = []
    current: list[AgenticAttributeSpec] = []
    for attribute in attributes:
        proposed = (*current, attribute)
        if (
            len(proposed) > max_attributes
            or _serialized_size(proposed) > max_request_bytes
            or _estimated_output_tokens(proposed) > max_estimated_output_tokens
        ):
            if not current:
                raise _target_too_large()
            groups.append(tuple(current))
            current = [attribute]
            if (
                _serialized_size(tuple(current)) > max_request_bytes
                or _estimated_output_tokens(tuple(current)) > max_estimated_output_tokens
            ):
                raise _target_too_large()
        else:
            current.append(attribute)
    if current:
        groups.append(tuple(current))
    return tuple(groups)


def _is_long_text(attribute: AgenticAttributeSpec) -> bool:
    return (
        attribute.data_type in {"string", "legacy_scalar"}
        and attribute.value_source == "free_text"
        and not attribute.allowed_values
        and not attribute.dictionary_values
    )


def _estimated_output_tokens(attributes: tuple[AgenticAttributeSpec, ...]) -> int:
    return sum(_attribute_output_tokens(attribute) for attribute in attributes)


def _attribute_output_tokens(attribute: AgenticAttributeSpec) -> int:
    if not _is_long_text(attribute):
        return 180
    maximum_length = attribute.constraints.get("max_length")
    if isinstance(maximum_length, int) and not isinstance(maximum_length, bool):
        # Value and literal quotes both occur in the response, plus JSON envelope overhead.
        return 192 + ceil(maximum_length / 2)
    return 900


def _target_too_large() -> PipelineStepError:
    return safe_context_resolver_error(
        code="AGENTIC_CONTEXT_RESOLVER_TARGET_TOO_LARGE",
        message="One Agentic Context Resolver target exceeds the request limit.",
    )


def _serialized_size(attributes: tuple[AgenticAttributeSpec, ...]) -> int:
    payload = {
        "targets": [
            {
                "handle": item.handle,
                "name": item.display_name,
                "type": item.data_type,
                "value_source": item.value_source,
                "constraints": dict(item.constraints),
                "allowed_values": [*item.allowed_values, *item.dictionary_values],
                "llm_context": item.llm_context,
            }
            for item in attributes
        ]
    }
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
