"""Safe normalization error helpers."""

from docmind_llmmagic.domain.pipeline.errors import PipelineStepError


def safe_normalization_error(*, code: str, message: str) -> PipelineStepError:
    """Return a sanitized pipeline step error for document normalization."""

    return PipelineStepError(code=code, message=message)
