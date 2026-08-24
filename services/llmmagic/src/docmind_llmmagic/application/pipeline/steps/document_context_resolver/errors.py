"""Safe Context Resolver error helpers."""

from docmind_llmmagic.domain.pipeline.errors import PipelineStepError


def safe_context_resolver_error(*, code: str, message: str) -> PipelineStepError:
    """Return a sanitized pipeline step error for Context Resolver failures."""

    return PipelineStepError(
        code=code,
        message=message,
    )
