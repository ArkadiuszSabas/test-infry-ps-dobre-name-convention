"""Validation helpers for the Context Resolver pipeline step."""

import re

from docmind_llmmagic.application.pipeline.steps.document_context_resolver.errors import (
    safe_context_resolver_error,
)
from docmind_llmmagic.domain.pipeline.context_resolution import (
    ContextResolutionDocumentStatus,
    ContextResolutionQualitySummary,
    ContextResolutionReasonCode,
    ResolvedDocumentAttribute,
)
from docmind_llmmagic.domain.pipeline.ocr import OcrDocumentArtifact, OcrPageStatus

_SAFE_REASON_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")


def validate_ocr_artifact(artifact: OcrDocumentArtifact) -> None:
    """Validate OCR artifact shape before context resolution starts."""

    if not artifact.pages:
        raise safe_context_resolver_error(
            code="CONTEXT_RESOLVER_OCR_PAGES_MISSING",
            message="Context Resolver requires OCR page artifacts.",
        )

    seen_page_numbers: set[int] = set()
    parsed_page_count = 0
    for page in artifact.pages:
        if page.page_number in seen_page_numbers:
            raise safe_context_resolver_error(
                code="CONTEXT_RESOLVER_DUPLICATE_PAGE_NUMBER",
                message="Context Resolver received duplicate OCR page numbers.",
            )
        seen_page_numbers.add(page.page_number)
        if page.status == OcrPageStatus.PARSED:
            parsed_page_count += 1

    if parsed_page_count == 0:
        raise safe_context_resolver_error(
            code="CONTEXT_RESOLVER_OCR_UNAVAILABLE",
            message="Context Resolver requires at least one parsed OCR page.",
        )


def validate_reason_codes(codes: tuple[ContextResolutionReasonCode, ...]) -> None:
    """Validate review reason codes before exposing resolved attributes."""

    if any(_SAFE_REASON_CODE_PATTERN.fullmatch(code.value) is None for code in codes):
        raise safe_context_resolver_error(
            code="CONTEXT_RESOLVER_REASON_CODE_INVALID",
            message="Context Resolver produced an invalid review reason code.",
        )


def quality_summary(
    attributes: tuple[ResolvedDocumentAttribute, ...],
) -> ContextResolutionQualitySummary:
    """Calculate safe aggregate context resolution quality metadata."""

    return ContextResolutionQualitySummary(
        resolved_attribute_count=sum(attribute.value is not None for attribute in attributes),
        review_required_attribute_count=sum(attribute.requires_review for attribute in attributes),
        missing_required_attribute_count=sum(
            ContextResolutionReasonCode.MISSING_REQUIRED_VALUE in attribute.reason_codes
            for attribute in attributes
        ),
        missing_attribute_count=sum(
            ContextResolutionReasonCode.MISSING_VALUE in attribute.reason_codes
            or ContextResolutionReasonCode.MISSING_REQUIRED_VALUE in attribute.reason_codes
            for attribute in attributes
        ),
        low_confidence_attribute_count=sum(
            ContextResolutionReasonCode.LOW_CONFIDENCE in attribute.reason_codes
            for attribute in attributes
        ),
        conflicting_attribute_count=sum(
            ContextResolutionReasonCode.CONFLICTING_VALUES in attribute.reason_codes
            or ContextResolutionReasonCode.KV_CONSISTENCY_CONFLICT in attribute.reason_codes
            for attribute in attributes
        ),
    )


def document_status(
    quality: ContextResolutionQualitySummary,
) -> ContextResolutionDocumentStatus:
    """Resolve aggregate context resolution status from quality metadata."""

    if quality.review_required_attribute_count:
        return ContextResolutionDocumentStatus.PARTIAL_FAILED

    return ContextResolutionDocumentStatus.SUCCEEDED
