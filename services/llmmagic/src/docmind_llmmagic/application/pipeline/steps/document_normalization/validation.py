"""Validation helpers for document field normalization."""

import re

from docmind_llmmagic.application.pipeline.steps.document_normalization.errors import (
    safe_normalization_error,
)
from docmind_llmmagic.domain.pipeline.normalization import (
    FieldReviewReasonCode,
    NormalizationDocumentStatus,
    NormalizationQualitySummary,
    NormalizedDocumentArtifact,
)
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrDocumentArtifact,
    OcrPageStatus,
)

_SAFE_REASON_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")


def validate_ocr_artifact(artifact: OcrDocumentArtifact) -> None:
    """Validate OCR artifact shape before field normalization starts."""

    if not artifact.pages:
        raise safe_normalization_error(
            code="NORMALIZATION_OCR_PAGES_MISSING",
            message="Document normalization requires OCR page artifacts.",
        )

    seen_page_numbers: set[int] = set()
    parsed_page_count = 0
    for page in artifact.pages:
        if page.page_number in seen_page_numbers:
            raise safe_normalization_error(
                code="NORMALIZATION_DUPLICATE_PAGE_NUMBER",
                message="Document normalization received duplicate page numbers.",
            )
        seen_page_numbers.add(page.page_number)
        if page.status == OcrPageStatus.PARSED:
            parsed_page_count += 1

    if parsed_page_count == 0:
        raise safe_normalization_error(
            code="NORMALIZATION_OCR_UNAVAILABLE",
            message="Document normalization requires at least one parsed OCR page.",
        )


def validate_reason_codes(codes: tuple[FieldReviewReasonCode, ...]) -> None:
    """Validate field review reason codes before exposing candidates."""

    if any(_SAFE_REASON_CODE_PATTERN.fullmatch(code.value) is None for code in codes):
        raise safe_normalization_error(
            code="NORMALIZATION_REASON_CODE_INVALID",
            message="Document normalization produced an invalid review reason code.",
        )


def quality_summary(artifact: NormalizedDocumentArtifact) -> NormalizationQualitySummary:
    """Calculate safe aggregate normalization quality metadata."""

    return NormalizationQualitySummary(
        review_required_candidate_count=sum(
            candidate.requires_review for candidate in artifact.candidates
        ),
        missing_required_candidate_count=sum(
            FieldReviewReasonCode.MISSING_REQUIRED_VALUE in candidate.reason_codes
            for candidate in artifact.candidates
        ),
        missing_candidate_count=sum(
            FieldReviewReasonCode.MISSING_VALUE in candidate.reason_codes
            or FieldReviewReasonCode.MISSING_REQUIRED_VALUE in candidate.reason_codes
            for candidate in artifact.candidates
        ),
        low_confidence_candidate_count=sum(
            FieldReviewReasonCode.LOW_CONFIDENCE in candidate.reason_codes
            for candidate in artifact.candidates
        ),
        conflicting_candidate_count=sum(
            FieldReviewReasonCode.CONFLICTING_VALUES in candidate.reason_codes
            for candidate in artifact.candidates
        ),
        unmapped_candidate_count=sum(
            FieldReviewReasonCode.ATTRIBUTE_MAPPING_MISSING in candidate.reason_codes
            for candidate in artifact.candidates
        ),
    )


def document_status(quality: NormalizationQualitySummary) -> NormalizationDocumentStatus:
    """Resolve aggregate normalization status from safe quality metadata."""

    if quality.review_required_candidate_count:
        return NormalizationDocumentStatus.PARTIAL_FAILED

    return NormalizationDocumentStatus.SUCCEEDED
