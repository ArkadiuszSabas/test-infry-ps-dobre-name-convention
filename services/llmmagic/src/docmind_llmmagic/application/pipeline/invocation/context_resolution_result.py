"""Safe Context Resolver result projection for pipeline invocation responses."""

from dataclasses import dataclass

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.constants import (
    CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.domain.pipeline.context_resolution import (
    AttributeConsistencyVerification,
    ContextResolutionArtifact,
    ContextResolutionQualitySummary,
    ResolvedAttributeSource,
    ResolvedAttributeStatus,
    ResolvedDocumentAttribute,
)
from docmind_llmmagic.domain.pipeline.models import PipelineContext

MAX_CONTEXT_RESOLUTION_ATTRIBUTE_COUNT = 500
MAX_CONTEXT_RESOLUTION_SOURCE_COUNT = 16
MAX_CONTEXT_RESOLUTION_REASON_CODE_COUNT = 16
MAX_CONTEXT_RESOLUTION_CONSISTENCY_COMPARISON_COUNT = 16
MAX_CONTEXT_RESOLUTION_TEXT_LENGTH = 1_000
MAX_CONTEXT_RESOLUTION_VALUE_LENGTH = 4_000


@dataclass(frozen=True, slots=True)
class PipelineInvocationContextResolutionQuality:
    """Safe aggregate quality metadata for context resolution."""

    resolved_attribute_count: int
    review_required_attribute_count: int
    missing_required_attribute_count: int
    missing_attribute_count: int
    low_confidence_attribute_count: int
    conflicting_attribute_count: int


@dataclass(frozen=True, slots=True)
class PipelineInvocationContextResolutionSource:
    """Safe source reference for one resolved attribute."""

    kind: str
    order_index: int | None
    page_number: int | None
    line_number: int | None
    key_value_index: int | None
    confidence: float | None
    bounding_polygon: tuple[float, ...] | None


@dataclass(frozen=True, slots=True)
class PipelineInvocationContextResolutionAttribute:
    """Safe resolved attribute returned by Context Resolver."""

    document_type_id: str | None
    attribute_external_id: str
    attribute_id: str | None
    display_name: str
    value_type: str | None
    required: bool
    value: str | None
    confidence_score: float | None
    status: str
    requires_review: bool
    sources: tuple[PipelineInvocationContextResolutionSource, ...]
    reason_codes: tuple[str, ...]
    consistency_status: str | None = None
    compared_values: tuple[str, ...] = ()
    compared_key_value_pages: tuple[int, ...] = ()
    compared_key_value_indexes: tuple[int, ...] = ()
    confidence_before: float | None = None
    confidence_after: float | None = None


@dataclass(frozen=True, slots=True)
class PipelineInvocationContextResolutionResult:
    """Safe Context Resolver result extracted from the pipeline context."""

    schema_version: int
    status: str
    document_type_id: str | None
    total_attribute_count: int
    quality: PipelineInvocationContextResolutionQuality
    attributes: tuple[PipelineInvocationContextResolutionAttribute, ...]


def context_resolution_result_from_context(
    context: PipelineContext,
) -> PipelineInvocationContextResolutionResult | None:
    """Return a bounded safe Context Resolver projection from the final context."""

    artifact = context.artifacts.get(CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY)
    if artifact is None or not isinstance(artifact.value, ContextResolutionArtifact):
        return None

    result = artifact.value
    return PipelineInvocationContextResolutionResult(
        schema_version=max(1, result.schema_version),
        status=result.status.value,
        document_type_id=_optional_text(result.document_type_id),
        total_attribute_count=max(0, result.total_attribute_count),
        quality=_quality(result.quality),
        attributes=tuple(
            _attribute(attribute)
            for attribute in result.attributes[:MAX_CONTEXT_RESOLUTION_ATTRIBUTE_COUNT]
        ),
    )


def _quality(
    quality: ContextResolutionQualitySummary,
) -> PipelineInvocationContextResolutionQuality:
    return PipelineInvocationContextResolutionQuality(
        resolved_attribute_count=max(0, quality.resolved_attribute_count),
        review_required_attribute_count=max(0, quality.review_required_attribute_count),
        missing_required_attribute_count=max(0, quality.missing_required_attribute_count),
        missing_attribute_count=max(0, quality.missing_attribute_count),
        low_confidence_attribute_count=max(0, quality.low_confidence_attribute_count),
        conflicting_attribute_count=max(0, quality.conflicting_attribute_count),
    )


def _attribute(
    attribute: ResolvedDocumentAttribute,
) -> PipelineInvocationContextResolutionAttribute:
    verification = attribute.consistency_verification
    comparison_entries = _comparison_entries(verification)
    return PipelineInvocationContextResolutionAttribute(
        document_type_id=_optional_text(attribute.document_type_id),
        attribute_external_id=_required_text(attribute.attribute_external_id, fallback="attribute"),
        attribute_id=_optional_text(attribute.attribute_id),
        display_name=_required_text(
            attribute.display_name, fallback=attribute.attribute_external_id
        ),
        value_type=_optional_text(attribute.value_type, max_length=64),
        required=attribute.required,
        value=_optional_text(attribute.value, max_length=MAX_CONTEXT_RESOLUTION_VALUE_LENGTH),
        confidence_score=_projected_confidence(attribute, verification=verification),
        status=attribute.status.value,
        requires_review=attribute.requires_review,
        sources=tuple(
            _source(source) for source in attribute.sources[:MAX_CONTEXT_RESOLUTION_SOURCE_COUNT]
        ),
        reason_codes=tuple(
            _required_text(reason_code.value, fallback="MODEL_OUTPUT_INVALID", max_length=80)
            for reason_code in attribute.reason_codes[:MAX_CONTEXT_RESOLUTION_REASON_CODE_COUNT]
        ),
        consistency_status=(verification.status.value if verification is not None else None),
        compared_values=tuple(
            _required_text(value, fallback="", max_length=MAX_CONTEXT_RESOLUTION_VALUE_LENGTH)
            for value, _page, _index in comparison_entries
        ),
        compared_key_value_pages=tuple(page for _value, page, _index in comparison_entries),
        compared_key_value_indexes=tuple(index for _value, _page, index in comparison_entries),
        confidence_before=(
            _confidence(verification.confidence_before) if verification is not None else None
        ),
        confidence_after=(
            _confidence(verification.confidence_after) if verification is not None else None
        ),
    )


def _comparison_entries(
    verification: AttributeConsistencyVerification | None,
) -> tuple[tuple[str, int, int], ...]:
    if verification is None:
        return ()

    return tuple(
        zip(
            verification.compared_values,
            verification.compared_key_value_pages,
            verification.compared_key_value_indexes,
            strict=False,
        )
    )[:MAX_CONTEXT_RESOLUTION_CONSISTENCY_COMPARISON_COUNT]


def _source(source: ResolvedAttributeSource) -> PipelineInvocationContextResolutionSource:
    return PipelineInvocationContextResolutionSource(
        kind=source.kind.value,
        order_index=_non_negative_int(source.order_index),
        page_number=_positive_int(source.page_number),
        line_number=_positive_int(source.line_number),
        key_value_index=_positive_int(source.key_value_index),
        confidence=_confidence(source.confidence),
        bounding_polygon=_normalized_polygon(source.bounding_polygon),
    )


def _required_text(
    value: str | None,
    *,
    fallback: str,
    max_length: int = MAX_CONTEXT_RESOLUTION_TEXT_LENGTH,
) -> str:
    text = _optional_text(value, max_length=max_length)
    if text is not None:
        return text

    return fallback[:max_length] or "value"


def _optional_text(
    value: str | None,
    *,
    max_length: int = MAX_CONTEXT_RESOLUTION_TEXT_LENGTH,
) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped[:max_length]


def _confidence(value: float | None) -> float | None:
    if value is None:
        return None
    return round(max(0.0, min(1.0, value)), 6)


def _projected_confidence(
    attribute: ResolvedDocumentAttribute,
    *,
    verification: AttributeConsistencyVerification | None,
) -> float | None:
    confidence = _confidence(attribute.confidence_score)
    if confidence is None or attribute.status is not ResolvedAttributeStatus.CONFLICTING:
        return confidence
    if verification is not None and verification.confidence_after is not None:
        return confidence
    return round(confidence * 0.5, 6)


def _positive_int(value: int | None) -> int | None:
    if value is None:
        return None
    return value if value > 0 else None


def _non_negative_int(value: int | None) -> int | None:
    if value is None:
        return None
    return value if value >= 0 else None


def _normalized_polygon(value: tuple[float, ...] | None) -> tuple[float, ...] | None:
    if value is None or len(value) < 8 or len(value) > 16 or len(value) % 2 != 0:
        return None
    return value if all(0 <= coordinate <= 1 for coordinate in value) else None
