"""Provider-neutral quality scores derived from terminal pipeline artifacts."""

from docmind_llmmagic.domain.pipeline.context_resolution import ContextResolutionArtifact
from docmind_llmmagic.domain.pipeline.models import PipelineResult
from docmind_llmmagic.domain.pipeline.ocr import OcrDocumentArtifact


def pipeline_quality_scores(result: PipelineResult) -> dict[str, float]:
    """Return bounded numeric scores available from a completed pipeline run."""

    scores: dict[str, float] = {}
    for artifact in result.context.artifacts.values():
        if isinstance(artifact.value, OcrDocumentArtifact):
            _add_ocr_scores(scores, artifact.value)
        elif isinstance(artifact.value, ContextResolutionArtifact):
            _add_context_resolution_scores(scores, artifact.value)

    retried_batch_count = sum(
        int(step.metrics.get("retried_batch_count", 0))
        for step in result.trace
        if isinstance(step.metrics.get("retried_batch_count", 0), int)
    )
    scores["context_resolver.retry_count"] = float(retried_batch_count)
    return scores


def _add_ocr_scores(scores: dict[str, float], artifact: OcrDocumentArtifact) -> None:
    scores["ocr.page_success_ratio"] = _ratio(
        artifact.succeeded_page_count,
        artifact.total_page_count,
    )
    if artifact.quality.average_confidence is not None:
        scores["ocr.average_confidence"] = _bounded(artifact.quality.average_confidence)
    if artifact.fallback_triggered_page_count > 0:
        scores["ocr.fallback_effectiveness"] = _ratio(
            artifact.fallback_succeeded_page_count,
            artifact.fallback_triggered_page_count,
        )


def _add_context_resolution_scores(
    scores: dict[str, float],
    artifact: ContextResolutionArtifact,
) -> None:
    total = artifact.total_attribute_count
    required = sum(attribute.required for attribute in artifact.attributes)
    required_resolved = sum(
        attribute.required and attribute.value is not None for attribute in artifact.attributes
    )
    scores.update(
        {
            "context_resolver.resolved_ratio": _ratio(
                artifact.quality.resolved_attribute_count,
                total,
            ),
            "context_resolver.required_completeness": _ratio(
                required_resolved,
                required,
                empty_value=1.0,
            ),
            "context_resolver.conflict_ratio": _ratio(
                artifact.quality.conflicting_attribute_count,
                total,
            ),
            "context_resolver.review_ratio": _ratio(
                artifact.quality.review_required_attribute_count,
                total,
            ),
            "context_resolver.exact_contract_validity": 1.0,
        }
    )


def _ratio(numerator: int, denominator: int, *, empty_value: float = 0.0) -> float:
    if denominator <= 0:
        return empty_value
    return _bounded(numerator / denominator)


def _bounded(value: float) -> float:
    return min(1.0, max(0.0, value))
