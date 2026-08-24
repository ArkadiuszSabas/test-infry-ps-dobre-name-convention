"""Cross-check Context Resolver attributes against OCR key-value sources."""

import re
import unicodedata
from dataclasses import replace
from datetime import datetime
from decimal import Decimal, InvalidOperation

from docmind_llmmagic.application.pipeline.engine.registry import StepFactoryRegistry
from docmind_llmmagic.application.pipeline.key_value_matching import (
    normalize_key_value_label,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.constants import (
    CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.application.pipeline.steps.document_context_resolver.validation import (
    document_status,
    quality_summary,
)
from docmind_llmmagic.application.pipeline.steps.document_kv_consistency.constants import (
    DOCUMENT_KV_CONSISTENCY_IMPLEMENTATION_ID,
)
from docmind_llmmagic.application.pipeline.steps.document_kv_consistency.source_recovery import (
    recover_ordered_source,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.constants import (
    OCR_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.domain.pipeline.context_resolution import (
    AttributeConsistencyStatus,
    AttributeConsistencyVerification,
    ContextResolutionArtifact,
    ContextResolutionReasonCode,
    ResolvedAttributeSourceKind,
    ResolvedAttributeStatus,
    ResolvedDocumentAttribute,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.models import (
    PipelineContext,
    PipelineStepDefinition,
    PipelineStepOutput,
)
from docmind_llmmagic.domain.pipeline.ocr import OcrDocumentArtifact, OcrPageArtifact


class DocumentKvConsistencyStep:
    """Add traceable consistency decisions without changing extracted values."""

    async def run(
        self,
        context: PipelineContext,
        definition: PipelineStepDefinition,
    ) -> PipelineStepOutput:
        resolution = _resolution_artifact(context)
        ocr_artifact = _ocr_artifact(context)
        values_by_source = _ocr_values_by_source(ocr_artifact)
        attributes = tuple(
            verify_attribute(attribute, values_by_source, pages=ocr_artifact.pages)
            for attribute in resolution.attributes
        )
        quality = quality_summary(attributes)
        updated = replace(
            resolution,
            schema_version=max(2, resolution.schema_version),
            status=document_status(quality),
            quality=quality,
            attributes=attributes,
        )
        metrics = _step_metrics(resolution.attributes, attributes)
        context.add_artifact(
            key=CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY,
            value=updated,
            produced_by_step_id=definition.step_id,
            metadata=metrics,
        )
        return PipelineStepOutput(metrics=metrics)


def register_document_kv_consistency_step(
    registry: StepFactoryRegistry,
    *,
    implementation_id: str = DOCUMENT_KV_CONSISTENCY_IMPLEMENTATION_ID,
) -> None:
    """Register the KV consistency verifier."""

    registry.register(implementation_id, lambda _definition: DocumentKvConsistencyStep())


def _resolution_artifact(context: PipelineContext) -> ContextResolutionArtifact:
    artifact = context.artifacts.get(CONTEXT_RESOLUTION_RESULT_ARTIFACT_KEY)
    if artifact is None or not isinstance(artifact.value, ContextResolutionArtifact):
        raise PipelineStepError(
            code="KV_CONSISTENCY_RESOLUTION_MISSING",
            message="KV consistency requires Context Resolver output.",
        )
    return artifact.value


def _ocr_artifact(context: PipelineContext) -> OcrDocumentArtifact:
    artifact = context.artifacts.get(OCR_RESULT_ARTIFACT_KEY)
    if artifact is None or not isinstance(artifact.value, OcrDocumentArtifact):
        raise PipelineStepError(
            code="KV_CONSISTENCY_OCR_MISSING",
            message="KV consistency requires OCR output.",
        )
    return artifact.value


def _ocr_values_by_source(
    artifact: OcrDocumentArtifact,
) -> dict[tuple[int, int], tuple[str, str]]:
    return {
        (pair.page_number, pair.order_index): (pair.key, pair.value)
        for pair in artifact.key_value_pairs
        if pair.order_index > 0 and pair.value.strip()
    }


def verify_attribute(
    attribute: ResolvedDocumentAttribute,
    values_by_source: dict[tuple[int, int], tuple[str, str]],
    *,
    pages: tuple[OcrPageArtifact, ...] = (),
) -> ResolvedDocumentAttribute:
    if any(
        source.kind == ResolvedAttributeSourceKind.DOCUMENT_METADATA for source in attribute.sources
    ):
        return replace(
            attribute,
            consistency_verification=AttributeConsistencyVerification(
                status=AttributeConsistencyStatus.NOT_COMPARABLE,
                compared_values=(),
                compared_key_value_indexes=(),
                compared_key_value_pages=(),
                confidence_before=_confidence_before(attribute),
            ),
        )
    source_keys = tuple(
        (source.page_number, source.key_value_index)
        for source in attribute.sources
        if source.kind == ResolvedAttributeSourceKind.OCR_KEY_VALUE
        and source.page_number is not None
        and source.key_value_index is not None
        and (source.page_number, source.key_value_index) in values_by_source
    )
    labels = {
        normalized
        for label in (attribute.attribute_external_id, attribute.display_name, *attribute.aliases)
        if (normalized := normalize_key_value_label(label))
    }
    matching_keys = tuple(
        key
        for key, (ocr_key, _value) in values_by_source.items()
        if normalize_key_value_label(ocr_key) in labels
    )
    source_keys = tuple(dict.fromkeys((*source_keys, *matching_keys)))
    values = tuple(values_by_source[source_key][1] for source_key in source_keys)
    normalized = {_normalize(value, attribute.value_type) for value in values}
    if not values:
        status = AttributeConsistencyStatus.NOT_COMPARABLE
    elif attribute.value is None:
        status = AttributeConsistencyStatus.CONFLICTING
    else:
        normalized.add(_normalize(attribute.value, attribute.value_type))
        status = (
            AttributeConsistencyStatus.CONSISTENT
            if len(normalized) == 1
            else AttributeConsistencyStatus.CONFLICTING
        )
    confidence_before = _confidence_before(attribute)
    verification = AttributeConsistencyVerification(
        status=status,
        compared_values=values,
        compared_key_value_indexes=tuple(index for _page, index in source_keys),
        compared_key_value_pages=tuple(page for page, _index in source_keys),
        confidence_before=confidence_before,
    )
    if status != AttributeConsistencyStatus.CONFLICTING:
        recovered_source = recover_ordered_source(
            attribute,
            matching_key_values=matching_keys,
            values_by_source=values_by_source,
            pages=pages,
            normalize_value=_normalize,
        )
        return replace(
            attribute,
            consistency_verification=verification,
            sources=(*attribute.sources, recovered_source)
            if recovered_source is not None
            else attribute.sources,
        )

    confidence = round((confidence_before or 0.0) * 0.5, 6)
    reasons = tuple(
        dict.fromkeys(
            (*attribute.reason_codes, ContextResolutionReasonCode.KV_CONSISTENCY_CONFLICT)
        )
    )
    return replace(
        attribute,
        confidence_score=confidence,
        status=ResolvedAttributeStatus.CONFLICTING,
        requires_review=True,
        reason_codes=reasons,
        consistency_verification=replace(
            verification,
            confidence_after=confidence,
            reason_code=ContextResolutionReasonCode.KV_CONSISTENCY_CONFLICT,
        ),
    )


def _normalize(value: str, value_type: str | None) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", value).split()).casefold()
    normalized_type = (value_type or "").casefold()
    if "id" in normalized_type:
        return re.sub(r"[\s-]", "", normalized)
    if normalized_type == "boolean":
        boolean = {
            "1": "true",
            "yes": "true",
            "tak": "true",
            "true": "true",
            "0": "false",
            "false": "false",
            "nie": "false",
            "no": "false",
        }.get(normalized)
        if boolean is not None:
            return boolean
    if normalized_type == "date":
        normalized = re.split(r"[T ]", normalized, maxsplit=1)[0]
        for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(normalized, date_format).date().isoformat()
            except ValueError:
                continue
    if normalized_type in {"currency", "number", "integer"}:
        numeric = _normalized_number(normalized)
        if numeric is not None:
            return numeric
    return normalized


def _normalized_number(value: str) -> str | None:
    candidate = re.sub(r"[^\d,.+-]", "", value)
    if not candidate or not any(character.isdigit() for character in candidate):
        return None
    if "," in candidate and "." in candidate:
        decimal_separator = "," if candidate.rfind(",") > candidate.rfind(".") else "."
        grouping_separator = "." if decimal_separator == "," else ","
        candidate = candidate.replace(grouping_separator, "").replace(decimal_separator, ".")
    elif "," in candidate:
        candidate = candidate.replace(",", ".")
    try:
        number = Decimal(candidate)
    except InvalidOperation:
        return None
    return format(number.normalize(), "f")


def _confidence_before(attribute: ResolvedDocumentAttribute) -> float | None:
    """Preserve the pre-verification confidence across repeated verifier blocks."""

    verification = attribute.consistency_verification
    if verification is not None and verification.confidence_before is not None:
        return verification.confidence_before
    return attribute.confidence_score


def _step_metrics(
    original_attributes: tuple[ResolvedDocumentAttribute, ...],
    verified_attributes: tuple[ResolvedDocumentAttribute, ...],
) -> dict[str, int]:
    verifications = tuple(attribute.consistency_verification for attribute in verified_attributes)
    return {
        "consistent_attribute_count": sum(
            verification is not None
            and verification.status == AttributeConsistencyStatus.CONSISTENT
            for verification in verifications
        ),
        "conflicting_attribute_count": sum(
            verification is not None
            and verification.status == AttributeConsistencyStatus.CONFLICTING
            for verification in verifications
        ),
        "attributes_missing_with_matching_kv": sum(
            original.value is None
            and verification is not None
            and bool(verification.compared_values)
            for original, verification in zip(
                original_attributes,
                verifications,
                strict=True,
            )
        ),
        "single_kv_consistent_count": sum(
            verification is not None
            and verification.status == AttributeConsistencyStatus.CONSISTENT
            and len(verification.compared_values) == 1
            for verification in verifications
        ),
        "single_kv_conflict_count": sum(
            verification is not None
            and verification.status == AttributeConsistencyStatus.CONFLICTING
            and len(verification.compared_values) == 1
            for verification in verifications
        ),
    }
