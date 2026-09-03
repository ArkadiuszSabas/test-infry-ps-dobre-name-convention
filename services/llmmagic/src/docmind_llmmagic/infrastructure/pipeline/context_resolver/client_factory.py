"""Construction and fail-closed fallback for the OpenAI Context Resolver client."""

from collections.abc import Sequence
from importlib import import_module
from typing import Any

from docmind_llmmagic.application.pipeline.observability import (
    ModelIdentity,
    PipelineObserver,
    TraceCaptureMode,
)
from docmind_llmmagic.application.pipeline.steps.document_agentic_context_resolver import (
    AgenticModelRequest,
    AgenticModelTurn,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.ports import (
    ContextResolverModelRequest,
    ContextResolverModelResult,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.openai import (
    OpenAIContextResolverClient,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.prompt import (
    DEFAULT_CONTEXT_RESOLVER_PROMPT_VERSION,
)
from docmind_llmmagic.infrastructure.pipeline.context_resolver.provider_completion import (
    OpenAIClient,
)


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

    async def agentic_turn(self, request: AgenticModelRequest) -> AgenticModelTurn:
        del request
        raise safe_context_resolver_error(
            code="AGENTIC_CONTEXT_RESOLVER_OPENAI_NOT_CONFIGURED",
            message="Agentic Context Resolver OpenAI provider is not configured.",
        )


def build_openai_context_resolver_client(
    *,
    default_model_id: str,
    request_timeout_seconds: float,
    base_url: str,
    max_request_bytes: int = 120_000,
    managed_identity_client_id: str | None = None,
    prompt_version: str = DEFAULT_CONTEXT_RESOLVER_PROMPT_VERSION,
    trace_capture_mode: TraceCaptureMode = TraceCaptureMode.METADATA,
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
    client: OpenAIClient = project_client.get_openai_client(
        timeout=request_timeout_seconds,
        max_retries=0,
    )
    return OpenAIContextResolverClient(
        client=client,
        default_model_id=default_model_id,
        request_timeout_seconds=request_timeout_seconds,
        max_request_bytes=max_request_bytes,
        prompt_version=prompt_version,
        trace_capture_mode=trace_capture_mode,
        model_tracer=model_tracer,
        model_identity=model_identity,
        model_identities=model_identities,
        resources=(project_client, credential),
    )


def _build_foundry_credential(*, managed_identity_client_id: str | None) -> object:
    identity_module = import_module("azure.identity.aio")
    if managed_identity_client_id:
        credential_class: Any = identity_module.__dict__["ManagedIdentityCredential"]
        return credential_class(client_id=managed_identity_client_id)
    credential_class = identity_module.__dict__["DefaultAzureCredential"]
    return credential_class()
