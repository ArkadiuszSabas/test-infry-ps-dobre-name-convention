"""Validation helpers for document preprocessing."""

import re

from docmind_llmmagic.application.pipeline.steps.document_preflight.validation import (
    is_safe_source_storage_reference,
    is_safe_storage_reference,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.errors import (
    safe_preprocessing_error,
    safe_preprocessing_page_error,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.ports import (
    TransformedPageContent,
)
from docmind_llmmagic.domain.pipeline.preflight import (
    DocumentInputKind,
    PreflightDocumentArtifact,
    PreflightDocumentStatus,
    PreflightPageArtifact,
    PreflightPageStatus,
)
from docmind_llmmagic.domain.pipeline.preprocessing import (
    ImagePreprocessingConfig,
    PreprocessedPageArtifact,
    PreprocessingDocumentArtifact,
    PreprocessingDocumentStatus,
    PreprocessingInputMode,
    PreprocessingPageStatus,
    SourcePdfDocumentContent,
    StoredPreprocessedDocumentArtifact,
    StoredPreprocessedPageArtifact,
    TransformedPdfDocumentContent,
)

_SAFE_ERROR_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")
_SAFE_CHECKSUM_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SAFE_ARTIFACT_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_preflight_artifact(artifact: PreflightDocumentArtifact) -> None:
    """Validate preflight artifact shape before preprocessing starts."""

    if artifact.status != PreflightDocumentStatus.SUCCEEDED:
        raise safe_preprocessing_error(
            code="PREPROCESSING_PREFLIGHT_NOT_PROCESSABLE",
            message="Document preprocessing requires a successful preflight artifact.",
        )
    if artifact.document_kind != DocumentInputKind.PDF:
        raise safe_preprocessing_error(
            code="PREPROCESSING_SOURCE_DOCUMENT_UNSUPPORTED",
            message="Document preprocessing requires a PDF source document.",
        )
    if not is_safe_source_storage_reference(artifact.source_storage_reference):
        raise safe_preprocessing_error(
            code="PREPROCESSING_SOURCE_REFERENCE_UNSUPPORTED",
            message="Document preprocessing source reference is not supported.",
        )


def validate_source_page(
    page: PreflightPageArtifact,
    config: ImagePreprocessingConfig,
) -> None:
    """Validate a preflight page before reading bytes from storage."""

    if page.status != PreflightPageStatus.PREPARED:
        raise safe_preprocessing_page_error("PREPROCESSING_INPUT_PAGE_FAILED")
    if page.storage_reference is None or not is_safe_storage_reference(page.storage_reference):
        raise safe_preprocessing_page_error("PREPROCESSING_INPUT_ARTIFACT_INVALID")
    if page.width_px is None or page.height_px is None or page.format is None:
        raise safe_preprocessing_page_error("PREPROCESSING_INPUT_ARTIFACT_INVALID")
    validate_dimensions(
        width_px=page.width_px,
        height_px=page.height_px,
        config=config,
        error_code="PREPROCESSING_INPUT_PAGE_TOO_LARGE",
    )


def validate_transformed_page(
    page: TransformedPageContent,
    config: ImagePreprocessingConfig,
    expected_page_number: int,
) -> None:
    """Validate transformed page metadata before storage."""

    if page.page_number != expected_page_number or page.page_number < 1 or not page.content:
        raise safe_preprocessing_page_error("PREPROCESSING_PAGE_ARTIFACT_INVALID")
    validate_dimensions(
        width_px=page.width_px,
        height_px=page.height_px,
        config=config,
        error_code="PREPROCESSING_OUTPUT_PAGE_TOO_LARGE",
    )
    validate_safe_codes(page.transformation.operation_codes)
    validate_safe_codes(page.transformation.warning_codes)


def validate_stored_processed_page(stored: StoredPreprocessedPageArtifact) -> None:
    """Validate storage metadata before exposing it to downstream steps."""

    if (
        not is_safe_storage_reference(stored.storage_reference)
        or _SAFE_CHECKSUM_PATTERN.fullmatch(stored.checksum) is None
        or _SAFE_ARTIFACT_VERSION_PATTERN.fullmatch(stored.artifact_version) is None
    ):
        raise safe_preprocessing_page_error("PREPROCESSING_PAGE_ARTIFACT_INVALID")


def validate_source_document_content(
    document: SourcePdfDocumentContent,
    *,
    expected_storage_reference: str,
    config: ImagePreprocessingConfig,
) -> None:
    """Validate source PDF bytes before CPU-heavy rendering starts."""

    if (
        document.storage_reference != expected_storage_reference
        or not document.content.startswith(b"%PDF-")
        or len(document.content) > config.max_source_document_bytes
    ):
        raise safe_preprocessing_error(
            code="PREPROCESSING_SOURCE_DOCUMENT_INVALID",
            message="Document preprocessing source PDF is invalid.",
        )


def validate_transformed_document(
    document: TransformedPdfDocumentContent,
    config: ImagePreprocessingConfig,
) -> None:
    """Validate a normalized PDF before writing it to storage."""

    if (
        document.page_count < config.min_processed_pages
        or document.dpi != config.target_dpi
        or not document.content.startswith(b"%PDF-")
        or len(document.content) > config.max_output_document_bytes
    ):
        raise safe_preprocessing_error(
            code="PREPROCESSING_OUTPUT_DOCUMENT_INVALID",
            message="Document preprocessing output PDF is invalid.",
        )
    validate_safe_codes(document.operation_codes)
    validate_safe_codes(document.warning_codes)


def validate_stored_processed_document(
    stored: StoredPreprocessedDocumentArtifact,
    *,
    source_storage_reference: str,
    expected_size_bytes: int,
) -> None:
    """Validate stored PDF metadata before exposing it to OCR."""

    if (
        stored.storage_reference == source_storage_reference
        or not is_safe_source_storage_reference(stored.storage_reference)
        or stored.size_bytes != expected_size_bytes
        or _SAFE_CHECKSUM_PATTERN.fullmatch(stored.checksum) is None
        or _SAFE_ARTIFACT_VERSION_PATTERN.fullmatch(stored.artifact_version) is None
    ):
        raise safe_preprocessing_error(
            code="PREPROCESSING_OUTPUT_DOCUMENT_INVALID",
            message="Stored preprocessing output is invalid.",
        )


def validate_document_outcome(
    artifact: PreprocessingDocumentArtifact,
    config: ImagePreprocessingConfig,
) -> None:
    """Validate aggregate document preprocessing thresholds."""

    del config
    if artifact.status != PreprocessingDocumentStatus.SUCCEEDED:
        raise safe_preprocessing_error(
            code="PREPROCESSING_DOCUMENT_NOT_PROCESSABLE",
            message="Document preprocessing did not produce a processable document.",
        )
    if not is_safe_source_storage_reference(artifact.ocr_input_storage_reference):
        raise safe_preprocessing_error(
            code="PREPROCESSING_OUTPUT_REFERENCE_UNSUPPORTED",
            message="Document preprocessing output reference is not supported.",
        )
    if artifact.document_kind != DocumentInputKind.PDF:
        raise safe_preprocessing_error(
            code="PREPROCESSING_SOURCE_DOCUMENT_UNSUPPORTED",
            message="Document preprocessing requires a PDF source document.",
        )
    if (
        artifact.input_mode != PreprocessingInputMode.NORMALIZED_DOCUMENT_REFERENCE
        or artifact.ocr_input_storage_reference == artifact.source_storage_reference
    ):
        raise safe_preprocessing_error(
            code="PREPROCESSING_OUTPUT_DOCUMENT_INVALID",
            message="Document preprocessing did not produce a normalized PDF.",
        )


def document_status(
    *,
    processed_page_count: int,
    failed_page_count: int,
    total_page_count: int,
    config: ImagePreprocessingConfig,
) -> PreprocessingDocumentStatus:
    """Resolve aggregate preprocessing status from page outcomes."""

    failed_ratio = failed_page_count / total_page_count if total_page_count else 1.0

    if (
        processed_page_count < config.min_processed_pages
        or failed_page_count > config.max_failed_pages
        or failed_ratio > config.max_failed_page_ratio
    ):
        return PreprocessingDocumentStatus.FAILED
    if failed_page_count:
        return PreprocessingDocumentStatus.PARTIAL_FAILED

    return PreprocessingDocumentStatus.SUCCEEDED


def validate_dimensions(
    *,
    width_px: int,
    height_px: int,
    config: ImagePreprocessingConfig,
    error_code: str,
) -> None:
    """Validate preprocessing page dimensions and megapixels."""

    if width_px < 1 or height_px < 1:
        raise safe_preprocessing_page_error("PREPROCESSING_PAGE_DIMENSIONS_INVALID")
    if width_px > config.max_page_width_px or height_px > config.max_page_height_px:
        raise safe_preprocessing_page_error(error_code)
    if (width_px * height_px) / 1_000_000 > config.max_page_megapixels:
        raise safe_preprocessing_page_error(error_code)


def validate_safe_codes(codes: tuple[str, ...]) -> None:
    """Validate operation, warning, and page error codes."""

    if any(_SAFE_ERROR_CODE_PATTERN.fullmatch(code) is None for code in codes):
        raise safe_preprocessing_page_error("PREPROCESSING_PAGE_ARTIFACT_INVALID")


def failed_page(
    *,
    page: PreflightPageArtifact,
    error_code: str,
) -> PreprocessedPageArtifact:
    """Build a safe failed page artifact from a preflight page."""

    validate_safe_codes((error_code,))
    source_storage_reference = (
        page.storage_reference
        if page.storage_reference is not None and is_safe_storage_reference(page.storage_reference)
        else None
    )
    return PreprocessedPageArtifact(
        page_number=page.page_number,
        status=PreprocessingPageStatus.FAILED,
        source_storage_reference=source_storage_reference,
        storage_reference=None,
        width_px=None,
        height_px=None,
        format=None,
        dpi=None,
        checksum=None,
        artifact_version=None,
        transformation=None,
        error_code=error_code,
    )
