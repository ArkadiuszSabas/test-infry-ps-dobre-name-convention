"""Document preflight domain contracts for OCR pipeline preparation."""

from dataclasses import dataclass
from enum import StrEnum


class DocumentInputKind(StrEnum):
    """Supported high-level input kinds for document preflight."""

    PDF = "pdf"
    IMAGE = "image"
    UNSUPPORTED = "unsupported"


class PreparedPageFormat(StrEnum):
    """Execution format for prepared page artifacts."""

    PNG = "png"


class PreflightDocumentStatus(StrEnum):
    """Aggregate document preparation status."""

    SUCCEEDED = "succeeded"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class PreflightPageStatus(StrEnum):
    """Preparation status for one document page."""

    PREPARED = "prepared"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class DocumentInputDescriptor:
    """Safe document metadata resolved from a document reference."""

    document_reference: str
    media_type: str
    size_bytes: int
    file_extension: str | None = None
    declared_page_count: int | None = None
    width_px: int | None = None
    height_px: int | None = None
    source_storage_reference: str | None = None
    content_checksum: str | None = None
    diagnostic_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PreflightLimits:
    """Configurable limits enforced before expensive OCR steps run."""

    max_document_bytes: int = 50 * 1024 * 1024
    max_pages: int = 200
    max_page_width_px: int = 10_000
    max_page_height_px: int = 10_000
    max_page_megapixels: float = 100.0
    max_processing_seconds: float = 120.0
    max_page_artifacts: int = 250
    min_prepared_pages: int = 1
    max_failed_pages: int = 0
    max_failed_page_ratio: float = 0.0
    supported_image_media_types: tuple[str, ...] = (
        "image/png",
        "image/jpeg",
        "image/tiff",
    )
    supported_image_extensions: tuple[str, ...] = ("png", "jpg", "jpeg", "tif", "tiff")


@dataclass(frozen=True, slots=True)
class PreparedPageCandidate:
    """Prepared page candidate produced by rendering/preparation adapters."""

    page_number: int
    width_px: int
    height_px: int
    checksum: str
    format: PreparedPageFormat = PreparedPageFormat.PNG
    dpi: int | None = None
    scale: float | None = None
    artifact_version: str = "preflight-page-v1"


@dataclass(frozen=True, slots=True)
class FailedPagePreparation:
    """Safe page-level preparation failure."""

    page_number: int
    error_code: str


type PagePreparationOutcome = PreparedPageCandidate | FailedPagePreparation


@dataclass(frozen=True, slots=True)
class StoredPageArtifact:
    """Storage result for one prepared page artifact."""

    storage_reference: str
    checksum: str
    artifact_version: str


@dataclass(frozen=True, slots=True)
class PreflightPageArtifact:
    """Byte-free page artifact metadata stored in the pipeline context."""

    page_number: int
    status: PreflightPageStatus
    width_px: int | None
    height_px: int | None
    format: PreparedPageFormat | None
    dpi: int | None
    scale: float | None
    checksum: str | None
    artifact_version: str | None
    storage_reference: str | None
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class PreflightDocumentArtifact:
    """Source document manifest stored in the pipeline context."""

    status: PreflightDocumentStatus
    document_kind: DocumentInputKind
    document_reference: str
    source_storage_reference: str
    media_type: str
    size_bytes: int
    file_extension: str | None = None
    declared_page_count: int | None = None
    width_px: int | None = None
    height_px: int | None = None
    content_checksum: str | None = None
    diagnostic_codes: tuple[str, ...] = ()
