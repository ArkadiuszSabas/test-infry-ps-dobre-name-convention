"""Safe Context Resolver error helpers."""

from docmind_llmmagic.domain.pipeline.errors import PipelineStepError


class ContextResolverModelCallError(PipelineStepError):
    """Safe model failure carrying the number of provider calls actually started."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        provider_request_count: int,
    ) -> None:
        if provider_request_count < 0:
            raise ValueError("provider_request_count must not be negative")
        super().__init__(code=code, message=message)
        self.provider_request_count = provider_request_count


def safe_context_resolver_error(*, code: str, message: str) -> PipelineStepError:
    """Return a sanitized pipeline step error for Context Resolver failures."""

    return PipelineStepError(
        code=code,
        message=message,
    )


def model_call_error(
    error: PipelineStepError,
    *,
    provider_request_count: int,
) -> ContextResolverModelCallError:
    """Preserve a safe error while attaching exact provider-call accounting."""

    return ContextResolverModelCallError(
        code=error.code,
        message=error.message,
        provider_request_count=provider_request_count,
    )


def provider_request_count_from_error(error: Exception, *, default: int) -> int:
    """Read exact provider-call accounting or use the caller's conservative default."""

    if isinstance(error, ContextResolverModelCallError):
        return error.provider_request_count
    return default
