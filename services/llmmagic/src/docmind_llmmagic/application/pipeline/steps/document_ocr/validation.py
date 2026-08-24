"""Validation helpers for document OCR/parsing."""

import re

from docmind_llmmagic.application.pipeline.steps.document_ocr.errors import (
    safe_ocr_error,
    safe_ocr_page_error,
)
from docmind_llmmagic.application.pipeline.steps.document_ocr.ports import OcrPageContent
from docmind_llmmagic.application.pipeline.steps.document_preflight.validation import (
    is_safe_storage_reference,
)
from docmind_llmmagic.domain.pipeline.ocr import (
    OcrDocumentArtifact,
    OcrDocumentStatus,
    OcrPageArtifact,
    OcrPageStatus,
    OcrParsingConfig,
    OcrProviderPageResult,
)
from docmind_llmmagic.domain.pipeline.preprocessing import (
    PreprocessedPageArtifact,
    PreprocessingDocumentArtifact,
    PreprocessingInputMode,
    PreprocessingPageStatus,
)

_SAFE_ERROR_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")


def validate_preprocessing_artifact(artifact: PreprocessingDocumentArtifact) -> None:
    """Validate preprocessing artifact shape before OCR starts."""

    if artifact.input_mode in {
        PreprocessingInputMode.SOURCE_DOCUMENT_REFERENCE,
        PreprocessingInputMode.NORMALIZED_DOCUMENT_REFERENCE,
    }:
        if not artifact.ocr_input_storage_reference:
            raise safe_ocr_error(
                code="OCR_INPUT_DOCUMENT_REFERENCE_MISSING",
                message="Document OCR requires a source document reference.",
            )
        return

    if not artifact.pages:
        raise safe_ocr_error(
            code="OCR_INPUT_PAGES_MISSING",
            message="Document OCR requires preprocessed page artifacts.",
        )

    seen_page_numbers: set[int] = set()
    for page in artifact.pages:
        if page.page_number in seen_page_numbers:
            raise safe_ocr_error(
                code="OCR_DUPLICATE_PAGE_NUMBER",
                message="Document OCR received duplicate page numbers.",
            )
        seen_page_numbers.add(page.page_number)


def validate_source_page(page: PreprocessedPageArtifact, config: OcrParsingConfig) -> None:
    """Validate a preprocessed page before reading bytes from storage."""

    if page.status != PreprocessingPageStatus.PROCESSED:
        raise safe_ocr_page_error("OCR_INPUT_PAGE_FAILED")
    if page.storage_reference is None or not is_safe_storage_reference(page.storage_reference):
        raise safe_ocr_page_error("OCR_INPUT_ARTIFACT_INVALID")
    if page.width_px is None or page.height_px is None or page.format is None:
        raise safe_ocr_page_error("OCR_INPUT_ARTIFACT_INVALID")
    validate_dimensions(
        width_px=page.width_px,
        height_px=page.height_px,
        config=config,
        error_code="OCR_INPUT_PAGE_TOO_LARGE",
    )


def validate_page_content(
    page: OcrPageContent,
    *,
    source_page: PreprocessedPageArtifact,
    config: OcrParsingConfig,
) -> None:
    """Validate page bytes and metadata before provider submission."""

    if page.page_number != source_page.page_number or page.page_number < 1 or not page.content:
        raise safe_ocr_page_error("OCR_INPUT_ARTIFACT_INVALID")
    if page.storage_reference != source_page.storage_reference or not is_safe_storage_reference(
        page.storage_reference
    ):
        raise safe_ocr_page_error("OCR_INPUT_ARTIFACT_INVALID")
    if page.format != source_page.format:
        raise safe_ocr_page_error("OCR_INPUT_ARTIFACT_INVALID")
    if page.width_px is not None and page.height_px is not None:
        validate_dimensions(
            width_px=page.width_px,
            height_px=page.height_px,
            config=config,
            error_code="OCR_INPUT_PAGE_TOO_LARGE",
        )


def validate_provider_result(
    result: OcrProviderPageResult,
    *,
    expected_page_number: int,
) -> None:
    """Validate provider output metadata before exposing it to the pipeline context."""

    if result.page_number != expected_page_number or result.page_number < 1:
        raise safe_ocr_page_error("OCR_PROVIDER_RESULT_INVALID")
    if result.confidence is not None and not 0 <= result.confidence <= 1:
        raise safe_ocr_page_error("OCR_PROVIDER_RESULT_INVALID")
    if result.provider_page_count < 1:
        raise safe_ocr_page_error("OCR_PROVIDER_RESULT_INVALID")
    validate_safe_codes(result.warning_codes)


def validate_document_outcome(
    artifact: OcrDocumentArtifact,
    config: OcrParsingConfig,
) -> None:
    """Validate aggregate document OCR/parsing thresholds."""

    if artifact.succeeded_page_count < config.min_succeeded_pages:
        raise safe_ocr_error(
            code="OCR_NO_PARSED_PAGES",
            message="Document OCR did not parse enough pages.",
        )
    if artifact.failed_page_count > config.max_failed_pages:
        raise safe_ocr_error(
            code="OCR_TOO_MANY_FAILED_PAGES",
            message="Document OCR exceeded the configured page failure limit.",
        )
    failed_ratio = (
        artifact.failed_page_count / artifact.total_page_count if artifact.total_page_count else 1.0
    )
    if failed_ratio > config.max_failed_page_ratio:
        raise safe_ocr_error(
            code="OCR_TOO_MANY_FAILED_PAGES",
            message="Document OCR exceeded the configured page failure ratio.",
        )


def document_status(
    *,
    succeeded_page_count: int,
    failed_page_count: int,
    total_page_count: int,
    config: OcrParsingConfig,
) -> OcrDocumentStatus:
    """Resolve aggregate OCR/parsing status from page outcomes."""

    failed_ratio = failed_page_count / total_page_count if total_page_count else 1.0
    if (
        succeeded_page_count < config.min_succeeded_pages
        or failed_page_count > config.max_failed_pages
        or failed_ratio > config.max_failed_page_ratio
    ):
        return OcrDocumentStatus.FAILED
    if failed_page_count:
        return OcrDocumentStatus.PARTIAL_FAILED

    return OcrDocumentStatus.SUCCEEDED


def validate_dimensions(
    *,
    width_px: int,
    height_px: int,
    config: OcrParsingConfig,
    error_code: str,
) -> None:
    """Validate OCR input page dimensions and megapixels."""

    if width_px < 1 or height_px < 1:
        raise safe_ocr_page_error("OCR_PAGE_DIMENSIONS_INVALID")
    if width_px > config.max_page_width_px or height_px > config.max_page_height_px:
        raise safe_ocr_page_error(error_code)
    if (width_px * height_px) / 1_000_000 > config.max_page_megapixels:
        raise safe_ocr_page_error(error_code)


def validate_safe_codes(codes: tuple[str, ...]) -> None:
    """Validate warning and page error codes."""

    if any(_SAFE_ERROR_CODE_PATTERN.fullmatch(code) is None for code in codes):
        raise safe_ocr_page_error("OCR_PROVIDER_RESULT_INVALID")


def failed_page(
    *,
    page: PreprocessedPageArtifact,
    config: OcrParsingConfig,
    error_code: str,
) -> OcrPageArtifact:
    """Build a safe failed OCR page artifact from a preprocessed page."""

    validate_safe_codes((error_code,))
    source_storage_reference = (
        page.storage_reference
        if page.storage_reference is not None and is_safe_storage_reference(page.storage_reference)
        else None
    )
    return OcrPageArtifact(
        page_number=page.page_number,
        status=OcrPageStatus.FAILED,
        source_storage_reference=source_storage_reference,
        text="",
        lines=(),
        words=(),
        width_px=None,
        height_px=None,
        format=None,
        dpi=None,
        provider_id=config.provider_id,
        model_id=config.model_id,
        confidence=None,
        error_code=error_code,
    )
