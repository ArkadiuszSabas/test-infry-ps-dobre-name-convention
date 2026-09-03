"""Safe provider error mapping for Context Resolver model requests."""

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError


def provider_request_error(error: Exception) -> PipelineStepError:
    """Map one provider failure to a stable pipeline error without leaking details."""

    status_code = _provider_status_code(error)
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


def _provider_status_code(error: Exception) -> int | None:
    for value in (
        getattr(error, "status_code", None),
        getattr(getattr(error, "response", None), "status_code", None),
    ):
        if isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599:
            return value
    return None
