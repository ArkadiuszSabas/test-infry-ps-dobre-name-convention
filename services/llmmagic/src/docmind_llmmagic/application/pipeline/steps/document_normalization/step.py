"""Document field normalization pipeline step implementation."""

import re
from dataclasses import dataclass

from docmind_llmmagic.application.pipeline.engine.registry import StepFactoryRegistry
from docmind_llmmagic.application.pipeline.steps.document_normalization.config import (
    normalization_config_from_mapping,
)
from docmind_llmmagic.application.pipeline.steps.document_normalization.constants import (
    DOCUMENT_NORMALIZATION_IMPLEMENTATION_ID,
)
from docmind_llmmagic.application.pipeline.steps.document_normalization.validation import (
    document_status,
    quality_summary,
    validate_ocr_artifact,
    validate_reason_codes,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.constants import (
    OCR_RESULT_ARTIFACT_KEY,
)
from docmind_llmmagic.domain.pipeline.errors import PipelineStepError
from docmind_llmmagic.domain.pipeline.models import (
    MetricValue,
    PipelineContext,
    PipelineStepDefinition,
    PipelineStepOutput,
)
from docmind_llmmagic.domain.pipeline.normalization import (
    AttributeNormalizationMapping,
    DocumentNormalizationConfig,
    FieldCandidateSource,
    FieldCandidateSourceKind,
    FieldCandidateStatus,
    FieldReviewReasonCode,
    NormalizationDocumentStatus,
    NormalizationQualitySummary,
    NormalizedDocumentArtifact,
    NormalizedFieldCandidate,
)
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrDocumentArtifact,
    OcrPageArtifact,
    OcrPageStatus,
)

NORMALIZATION_RESULT_ARTIFACT_KEY = "document.normalization.result"


@dataclass(frozen=True, slots=True)
class _CandidateMatch:
    value: str
    source: FieldCandidateSource
    confidence: float | None


class DocumentNormalizationStep:
    """Normalize OCR/parsing output into document field candidates."""

    async def run(
        self,
        context: PipelineContext,
        definition: PipelineStepDefinition,
    ) -> PipelineStepOutput:
        """Run field normalization and expose candidates as a pipeline artifact."""

        config = normalization_config_from_mapping(definition.config)
        ocr_artifact = _ocr_artifact_from_context(context)
        validate_ocr_artifact(ocr_artifact)

        candidates = _field_candidates(config=config, ocr_artifact=ocr_artifact)
        quality = _candidate_quality(candidates)
        document_artifact = NormalizedDocumentArtifact(
            status=document_status(quality),
            document_type_id=config.document_type_id,
            total_candidate_count=len(candidates),
            mapped_candidate_count=sum(
                candidate.attribute_id is not None for candidate in candidates
            ),
            quality=quality,
            candidates=tuple(candidates),
        )
        context.add_artifact(
            key=NORMALIZATION_RESULT_ARTIFACT_KEY,
            value=document_artifact,
            produced_by_step_id=definition.step_id,
            metadata=_artifact_metadata(document_artifact),
        )

        return PipelineStepOutput(metrics=_step_metrics(document_artifact))


def register_document_normalization_step(
    registry: StepFactoryRegistry,
    *,
    implementation_id: str = DOCUMENT_NORMALIZATION_IMPLEMENTATION_ID,
) -> None:
    """Register the document field normalization step implementation."""

    registry.register(implementation_id, lambda _definition: DocumentNormalizationStep())


def _ocr_artifact_from_context(context: PipelineContext) -> OcrDocumentArtifact:
    artifact = context.artifacts.get(OCR_RESULT_ARTIFACT_KEY)
    value = artifact.value if artifact is not None else None
    if not isinstance(value, OcrDocumentArtifact):
        raise PipelineStepError(
            code="NORMALIZATION_OCR_MISSING",
            message="Document normalization requires OCR/parsing artifacts.",
        )

    return value


def _field_candidates(
    *,
    config: DocumentNormalizationConfig,
    ocr_artifact: OcrDocumentArtifact,
) -> list[NormalizedFieldCandidate]:
    candidates: list[NormalizedFieldCandidate] = []
    for mapping in config.attributes:
        matches = _matches_for_mapping(mapping=mapping, ocr_artifact=ocr_artifact)
        candidates.extend(_candidates_for_mapping(config=config, mapping=mapping, matches=matches))

    return candidates


def _matches_for_mapping(
    *,
    mapping: AttributeNormalizationMapping,
    ocr_artifact: OcrDocumentArtifact,
) -> list[_CandidateMatch]:
    matches: list[_CandidateMatch] = []
    for page in ocr_artifact.pages:
        if page.status != OcrPageStatus.PARSED:
            continue
        for line_number, line_content in _page_lines(page):
            value = _labeled_value(line_content, mapping.labels)
            if value is None:
                continue
            matches.append(
                _CandidateMatch(
                    value=value,
                    source=FieldCandidateSource(
                        kind=FieldCandidateSourceKind.OCR_LINE,
                        page_number=page.page_number,
                        line_number=line_number,
                        confidence=page.confidence,
                    ),
                    confidence=page.confidence,
                )
            )

    return matches


def _page_lines(page: OcrPageArtifact) -> tuple[tuple[int, str], ...]:
    if page.lines:
        return tuple((index, line.content) for index, line in enumerate(page.lines, start=1))

    return tuple(
        (index, line) for index, line in enumerate(page.text.splitlines(), start=1) if line.strip()
    )


def _labeled_value(line: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        match = re.match(rf"^\s*{re.escape(label)}\s*[:=]\s*(?P<value>.+?)\s*$", line, re.I)
        if match is None:
            continue
        value = match.group("value").strip()
        if value:
            return value

    return None


def _candidates_for_mapping(
    *,
    config: DocumentNormalizationConfig,
    mapping: AttributeNormalizationMapping,
    matches: list[_CandidateMatch],
) -> list[NormalizedFieldCandidate]:
    if not matches:
        return [_missing_candidate(config=config, mapping=mapping)]

    matches_by_value: dict[str, list[_CandidateMatch]] = {}
    for match in matches:
        matches_by_value.setdefault(match.value, []).append(match)

    conflicting = len(matches_by_value) > 1
    return [
        _present_candidate(
            config=config,
            mapping=mapping,
            value=value,
            matches=value_matches,
            conflicting=conflicting,
        )
        for value, value_matches in sorted(matches_by_value.items())
    ]


def _missing_candidate(
    *,
    config: DocumentNormalizationConfig,
    mapping: AttributeNormalizationMapping,
) -> NormalizedFieldCandidate:
    reason_code = (
        FieldReviewReasonCode.MISSING_REQUIRED_VALUE
        if mapping.required
        else FieldReviewReasonCode.MISSING_VALUE
    )
    reason_codes = _reason_codes(mapping=mapping, extra_reason_codes=(reason_code,))
    requires_review = bool(reason_codes)
    return NormalizedFieldCandidate(
        document_type_id=config.document_type_id,
        attribute_external_id=mapping.attribute_external_id,
        attribute_id=mapping.attribute_id,
        value=None,
        sources=(
            FieldCandidateSource(
                kind=FieldCandidateSourceKind.MISSING,
            ),
        ),
        confidence=None,
        status=FieldCandidateStatus.MISSING,
        requires_review=requires_review,
        reason_codes=reason_codes,
    )


def _present_candidate(
    *,
    config: DocumentNormalizationConfig,
    mapping: AttributeNormalizationMapping,
    value: str,
    matches: list[_CandidateMatch],
    conflicting: bool,
) -> NormalizedFieldCandidate:
    confidence = _average_confidence(matches)
    extra_reason_codes: list[FieldReviewReasonCode] = []
    status = FieldCandidateStatus.PRESENT

    if conflicting:
        extra_reason_codes.append(FieldReviewReasonCode.CONFLICTING_VALUES)
        status = FieldCandidateStatus.CONFLICTING
    if confidence is None or confidence < config.low_confidence_threshold:
        extra_reason_codes.append(FieldReviewReasonCode.LOW_CONFIDENCE)
        if not conflicting:
            status = FieldCandidateStatus.UNCERTAIN

    reason_codes = _reason_codes(mapping=mapping, extra_reason_codes=tuple(extra_reason_codes))
    return NormalizedFieldCandidate(
        document_type_id=config.document_type_id,
        attribute_external_id=mapping.attribute_external_id,
        attribute_id=mapping.attribute_id,
        value=value,
        sources=tuple(match.source for match in matches),
        confidence=confidence,
        status=status,
        requires_review=bool(reason_codes),
        reason_codes=reason_codes,
    )


def _reason_codes(
    *,
    mapping: AttributeNormalizationMapping,
    extra_reason_codes: tuple[FieldReviewReasonCode, ...],
) -> tuple[FieldReviewReasonCode, ...]:
    reason_codes: list[FieldReviewReasonCode] = []
    if mapping.attribute_id is None:
        reason_codes.append(FieldReviewReasonCode.ATTRIBUTE_MAPPING_MISSING)
    reason_codes.extend(extra_reason_codes)
    result = tuple(reason_codes)
    validate_reason_codes(result)
    return result


def _average_confidence(matches: list[_CandidateMatch]) -> float | None:
    confidence_values = [match.confidence for match in matches if match.confidence is not None]
    if not confidence_values:
        return None

    return round(sum(confidence_values) / len(confidence_values), 6)


def _candidate_quality(
    candidates: list[NormalizedFieldCandidate],
) -> NormalizationQualitySummary:
    placeholder_artifact = NormalizedDocumentArtifact(
        status=NormalizationDocumentStatus.SUCCEEDED,
        document_type_id=None,
        total_candidate_count=len(candidates),
        mapped_candidate_count=sum(candidate.attribute_id is not None for candidate in candidates),
        quality=NormalizationQualitySummary(
            review_required_candidate_count=0,
            missing_required_candidate_count=0,
            missing_candidate_count=0,
            low_confidence_candidate_count=0,
            conflicting_candidate_count=0,
            unmapped_candidate_count=0,
        ),
        candidates=tuple(candidates),
    )
    return quality_summary(placeholder_artifact)


def _artifact_metadata(artifact: NormalizedDocumentArtifact) -> dict[str, MetricValue]:
    return _step_metrics(artifact)


def _step_metrics(artifact: NormalizedDocumentArtifact) -> dict[str, MetricValue]:
    metrics: dict[str, MetricValue] = {
        "candidate_count": artifact.total_candidate_count,
        "mapped_candidate_count": artifact.mapped_candidate_count,
        "review_required_candidate_count": artifact.quality.review_required_candidate_count,
        "missing_required_candidate_count": artifact.quality.missing_required_candidate_count,
        "missing_candidate_count": artifact.quality.missing_candidate_count,
        "low_confidence_candidate_count": artifact.quality.low_confidence_candidate_count,
        "conflicting_candidate_count": artifact.quality.conflicting_candidate_count,
        "unmapped_candidate_count": artifact.quality.unmapped_candidate_count,
        "partial_normalization": artifact.status == NormalizationDocumentStatus.PARTIAL_FAILED,
    }

    return metrics
