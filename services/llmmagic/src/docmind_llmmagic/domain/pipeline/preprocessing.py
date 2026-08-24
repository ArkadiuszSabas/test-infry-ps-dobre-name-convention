"""Document preprocessing domain contracts for OCR pipeline preparation."""

from dataclasses import dataclass
from enum import StrEnum

from docmind_llmmagic.domain.pipeline.preflight import DocumentInputKind, PreparedPageFormat


class PreprocessingDocumentStatus(StrEnum):
    """Aggregate document preprocessing status."""

    SUCCEEDED = "succeeded"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class PreprocessingPageStatus(StrEnum):
    """Preprocessing status for one document page."""

    PROCESSED = "processed"
    FAILED = "failed"


class PreprocessingInputMode(StrEnum):
    """Document-level input mode exposed to downstream OCR."""

    SOURCE_DOCUMENT_REFERENCE = "source_document_reference"
    NORMALIZED_DOCUMENT_REFERENCE = "normalized_document_reference"
    PAGE_IMAGE_ARTIFACTS = "page_image_artifacts"


@dataclass(frozen=True, slots=True)
class ImagePreprocessingConfig:
    """Validated deterministic image preprocessing configuration."""

    preset_id: str = "ocr_default"
    algorithm_version: str = "opencv-preprocessing-v2"
    target_format: PreparedPageFormat = PreparedPageFormat.PNG
    target_dpi: int = 300
    max_source_document_bytes: int = 50 * 1024 * 1024
    max_output_document_bytes: int = 250 * 1024 * 1024
    max_pages: int = 200
    max_page_width_px: int = 10_000
    max_page_height_px: int = 10_000
    max_page_megapixels: float = 100.0
    max_processing_seconds: float = 120.0
    min_processed_pages: int = 1
    max_failed_pages: int = 0
    max_failed_page_ratio: float = 0.0
    normalize_format: bool = True
    auto_orient: bool = True
    rotation_degrees: float = 0.0
    deskew: bool = False
    max_deskew_degrees: float = 10.0
    grayscale: bool = True
    enhance_contrast: bool = False
    denoise: bool = True
    bilateral_diameter: int = 5
    bilateral_sigma_color: float = 25.0
    bilateral_sigma_space: float = 25.0
    normalize_dpi: bool = True


@dataclass(frozen=True, slots=True)
class ImageTransformationMetadata:
    """Byte-free metadata describing deterministic image transformations."""

    algorithm_version: str
    preset_id: str
    source_width_px: int
    source_height_px: int
    output_width_px: int
    output_height_px: int
    source_dpi: int | None
    output_dpi: int | None
    scale: float
    rotation_degrees: float
    deskew_degrees: float
    format_normalized: bool
    grayscale_applied: bool
    contrast_enhanced: bool
    denoised: bool
    operation_codes: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StoredPreprocessedPageArtifact:
    """Storage result for one preprocessed page artifact."""

    storage_reference: str
    checksum: str
    artifact_version: str


@dataclass(frozen=True, slots=True)
class SourcePdfDocumentContent:
    """Source PDF bytes read from an internal document store."""

    storage_reference: str
    content: bytes


@dataclass(frozen=True, slots=True)
class TransformedPdfDocumentContent:
    """Preprocessed PDF bytes and safe transformation metadata."""

    content: bytes
    page_count: int
    dpi: int
    operation_codes: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StoredPreprocessedDocumentArtifact:
    """Storage result for a preprocessed PDF document."""

    storage_reference: str
    size_bytes: int
    checksum: str
    artifact_version: str


@dataclass(frozen=True, slots=True)
class PreprocessedPageArtifact:
    """Byte-free preprocessed page artifact metadata stored in pipeline context."""

    page_number: int
    status: PreprocessingPageStatus
    source_storage_reference: str | None
    storage_reference: str | None
    width_px: int | None
    height_px: int | None
    format: PreparedPageFormat | None
    dpi: int | None
    checksum: str | None
    artifact_version: str | None
    transformation: ImageTransformationMetadata | None
    warning_codes: tuple[str, ...] = ()
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class PreprocessingDocumentArtifact:
    """Document-level preprocessing artifact stored in pipeline context."""

    status: PreprocessingDocumentStatus
    preset_id: str
    algorithm_version: str
    input_mode: PreprocessingInputMode
    document_kind: DocumentInputKind
    source_storage_reference: str
    ocr_input_storage_reference: str
    media_type: str
    size_bytes: int
    file_extension: str | None = None
    declared_page_count: int | None = None
    width_px: int | None = None
    height_px: int | None = None
    diagnostic_codes: tuple[str, ...] = ()
    total_page_count: int = 0
    processed_page_count: int = 0
    failed_page_count: int = 0
    pages: tuple[PreprocessedPageArtifact, ...] = ()
