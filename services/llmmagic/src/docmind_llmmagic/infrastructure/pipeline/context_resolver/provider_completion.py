"""OpenAI transport and bounded response helpers for Context Resolver."""

from collections.abc import Mapping, Sequence
from typing import Protocol, cast

from docmind_llmmagic.infrastructure.pipeline.context_resolver.telemetry import (
    ModelResponseMetadata,
)

_MAX_MODEL_RESPONSE_CHARS = 100_000


class ChatCompletions(Protocol):
    """Minimal async Chat Completions surface used by the adapter."""

    async def create(self, **kwargs: object) -> object: ...


class ChatResource(Protocol):
    """Minimal chat resource surface used by the adapter."""

    completions: ChatCompletions


class OpenAIClient(Protocol):
    """Minimal OpenAI client surface used by the adapter."""

    chat: ChatResource


async def create_chat_completion(
    client: OpenAIClient,
    *,
    create_kwargs: Mapping[str, object],
) -> object:
    """Invoke the provider with the already measured exact arguments."""

    return await client.chat.completions.create(**dict(create_kwargs))


def validate_completion_state(metadata: ModelResponseMetadata) -> None:
    """Reject refusals and incomplete completions before payload parsing."""

    if metadata.refusal or metadata.incomplete or metadata.finish_reason != "stop":
        raise ValueError("model response did not complete successfully")


def bounded_response_content(response: object) -> str:
    """Return one bounded non-empty response body."""

    choices = getattr(response, "choices", ())
    if not isinstance(choices, Sequence) or not choices:
        raise ValueError("missing response content")
    message = getattr(cast(Sequence[object], choices)[0], "message", None)
    content = getattr(message, "content", None)
    if not isinstance(content, str) or not content:
        raise ValueError("missing response content")
    if len(content) > _MAX_MODEL_RESPONSE_CHARS:
        raise ValueError("response content exceeds safe limit")
    return content
