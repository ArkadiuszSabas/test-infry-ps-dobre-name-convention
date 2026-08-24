"""Safe preflight error helpers."""

from docmind_llmmagic.domain.pipeline.errors import PipelineStepError


def safe_preflight_error(*, code: str, message: str) -> PipelineStepError:
    """Return a sanitized pipeline step error for document preflight."""

    return PipelineStepError(code=code, message=message)
