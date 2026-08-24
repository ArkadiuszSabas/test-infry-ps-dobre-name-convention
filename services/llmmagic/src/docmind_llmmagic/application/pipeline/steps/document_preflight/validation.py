"""Validation helpers for document preflight."""

import re
from urllib.parse import urlsplit

from docmind_llmmagic.application.pipeline.steps.document_preflight.errors import (
    safe_preflight_error,
)
from docmind_llmmagic.domain.pipeline.preflight import (
    DocumentInputDescriptor,
    DocumentInputKind,
    FailedPagePreparation,
    PreflightDocumentArtifact,
    PreflightLimits,
    PreparedPageCandidate,
    StoredPageArtifact,
)

_SAFE_ERROR_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")
_SAFE_CHECKSUM_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SAFE_ARTIFACT_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SAFE_CONTENT_CHECKSUM_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SAFE_STORAGE_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SAFE_SOURCE_BLOB_SEGMENT_PATTERN = re.compile(
    r"^(?:[A-Za-z0-9]|%[0-9A-Fa-f]{2})"
    r"(?:[A-Za-z0-9._-]|%[0-9A-Fa-f]{2}){0,127}$"
)
_SAFE_STORAGE_REFERENCE_SCHEMES = frozenset({"store"})
_SAFE_SOURCE_REFERENCE_SCHEMES = frozenset({"azblob", "https"})


def classify_document(
    descriptor: DocumentInputDescriptor,
    limits: PreflightLimits,
) -> DocumentInputKind:
    """Classify a document descriptor as PDF or supported image."""

    media_type = descriptor.media_type.lower()
    extension = (descriptor.file_extension or "").lower().lstrip(".")

    if media_type == "application/pdf" or extension == "pdf":
        return DocumentInputKind.PDF
    if (
        media_type in limits.supported_image_media_types
        or extension in limits.supported_image_extensions
    ):
        return DocumentInputKind.IMAGE

    raise safe_preflight_error(
        code="PREFLIGHT_UNSUPPORTED_DOCUMENT_TYPE",
        message="Document type is not supported for OCR preflight.",
    )


def validate_descriptor(
    descriptor: DocumentInputDescriptor,
    expected_document_reference: str,
) -> None:
    """Validate safe metadata returned for the requested document reference."""

    if descriptor.document_reference != expected_document_reference:
        raise safe_preflight_error(
            code="PREFLIGHT_DESCRIPTOR_MISMATCH",
            message="Document metadata does not match the requested document reference.",
        )
    if descriptor.size_bytes < 0:
        raise safe_preflight_error(
            code="PREFLIGHT_DESCRIPTOR_INVALID",
            message="Document metadata is invalid.",
        )
    if (
        descriptor.content_checksum is not None
        and _SAFE_CONTENT_CHECKSUM_PATTERN.fullmatch(descriptor.content_checksum) is None
    ):
        raise safe_preflight_error(
            code="PREFLIGHT_DESCRIPTOR_INVALID",
            message="Document metadata is invalid.",
        )
    if any(
        _SAFE_ERROR_CODE_PATTERN.fullmatch(code) is None for code in descriptor.diagnostic_codes
    ):
        raise safe_preflight_error(
            code="PREFLIGHT_DESCRIPTOR_INVALID",
            message="Document metadata is invalid.",
        )
    if not is_safe_source_storage_reference(descriptor.document_reference):
        raise safe_preflight_error(
            code="PREFLIGHT_SOURCE_REFERENCE_UNSUPPORTED",
            message="Document source reference is not supported for OCR preflight.",
        )
    if descriptor.source_storage_reference is not None and not is_safe_source_storage_reference(
        descriptor.source_storage_reference
    ):
        raise safe_preflight_error(
            code="PREFLIGHT_SOURCE_REFERENCE_UNSUPPORTED",
            message="Document source reference is not supported for OCR preflight.",
        )


def validate_document_limits(
    descriptor: DocumentInputDescriptor,
    limits: PreflightLimits,
) -> None:
    """Validate document-level limits before page preparation starts."""

    if descriptor.size_bytes > limits.max_document_bytes:
        raise safe_preflight_error(
            code="PREFLIGHT_DOCUMENT_TOO_LARGE",
            message="Document exceeds the configured size limit.",
        )
    if (
        descriptor.declared_page_count is not None
        and descriptor.declared_page_count > limits.max_pages
    ):
        raise safe_preflight_error(
            code="PREFLIGHT_TOO_MANY_PAGES",
            message="Document exceeds the configured page limit.",
        )
    if descriptor.width_px is not None and descriptor.height_px is not None:
        validate_dimensions(
            width_px=descriptor.width_px,
            height_px=descriptor.height_px,
            limits=limits,
        )


def validate_page_candidate(
    page: PreparedPageCandidate,
    limits: PreflightLimits,
) -> None:
    """Validate a prepared page before storage."""

    if (
        page.page_number < 1
        or not _is_safe_checksum(page.checksum)
        or not _is_safe_artifact_version(page.artifact_version)
    ):
        raise safe_preflight_error(
            code="PREFLIGHT_PAGE_ARTIFACT_INVALID",
            message="Prepared page artifact metadata is invalid.",
        )
    validate_dimensions(
        width_px=page.width_px,
        height_px=page.height_px,
        limits=limits,
    )


def validate_failed_page_preparation(page: FailedPagePreparation) -> None:
    """Validate safe page-level failure metadata before storing it in context."""

    if page.page_number < 1 or _SAFE_ERROR_CODE_PATTERN.fullmatch(page.error_code) is None:
        raise safe_preflight_error(
            code="PREFLIGHT_PAGE_FAILURE_INVALID",
            message="Page preparation failure metadata is invalid.",
        )


def validate_dimensions(*, width_px: int, height_px: int, limits: PreflightLimits) -> None:
    """Validate page dimensions and megapixels."""

    if width_px < 1 or height_px < 1:
        raise safe_preflight_error(
            code="PREFLIGHT_PAGE_DIMENSIONS_INVALID",
            message="Prepared page dimensions are invalid.",
        )
    if width_px > limits.max_page_width_px or height_px > limits.max_page_height_px:
        raise safe_preflight_error(
            code="PREFLIGHT_PAGE_TOO_LARGE",
            message="Prepared page exceeds the configured dimension limit.",
        )
    if (width_px * height_px) / 1_000_000 > limits.max_page_megapixels:
        raise safe_preflight_error(
            code="PREFLIGHT_PAGE_TOO_LARGE",
            message="Prepared page exceeds the configured megapixel limit.",
        )


def validate_stored_page(stored: StoredPageArtifact) -> None:
    """Validate storage metadata before exposing it to downstream steps."""

    if (
        not is_safe_storage_reference(stored.storage_reference)
        or not _is_safe_checksum(stored.checksum)
        or not _is_safe_artifact_version(stored.artifact_version)
    ):
        raise safe_preflight_error(
            code="PREFLIGHT_PAGE_ARTIFACT_INVALID",
            message="Stored page artifact metadata is invalid.",
        )


def validate_document_outcome(
    artifact: PreflightDocumentArtifact,
    limits: PreflightLimits,
) -> None:
    """Validate aggregate document preparation thresholds."""

    del limits
    if artifact.document_kind == DocumentInputKind.UNSUPPORTED:
        raise safe_preflight_error(
            code="PREFLIGHT_UNSUPPORTED_DOCUMENT_TYPE",
            message="Document type is not supported for OCR preflight.",
        )


def is_safe_storage_reference(value: str) -> bool:
    """Allow only opaque non-secret storage references in preflight artifacts."""

    if not value or "\\" in value:
        return False
    parsed = urlsplit(value)
    if parsed.scheme not in _SAFE_STORAGE_REFERENCE_SCHEMES:
        return False
    if (
        not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return False
    if not _is_safe_storage_segment(parsed.netloc):
        return False
    if not parsed.path.startswith("/"):
        return False

    path_segments = parsed.path.removeprefix("/").split("/")
    if not path_segments:
        return False

    return all(_is_safe_storage_segment(segment) for segment in path_segments)


def is_safe_source_storage_reference(value: str) -> bool:
    """Allow only non-secret source document references for provider input preparation."""

    if not value or "\\" in value:
        return False
    parsed = urlsplit(value)
    if parsed.scheme not in _SAFE_SOURCE_REFERENCE_SCHEMES:
        return False
    if (
        not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return False
    if parsed.scheme == "https" and not parsed.netloc.lower().endswith(".blob.core.windows.net"):
        return False
    if parsed.scheme == "azblob" and not _is_safe_storage_segment(parsed.netloc):
        return False
    if not parsed.path.startswith("/"):
        return False

    path_segments = parsed.path.removeprefix("/").split("/")
    if not path_segments:
        return False
    if parsed.scheme == "https":
        if len(path_segments) < 2 or not _is_safe_storage_segment(path_segments[0]):
            return False
        path_segments = path_segments[1:]

    return all(_is_safe_source_blob_segment(segment) for segment in path_segments)


def _is_safe_storage_segment(value: str) -> bool:
    if value in {".", ".."}:
        return False

    return _SAFE_STORAGE_SEGMENT_PATTERN.fullmatch(value) is not None


def _is_safe_source_blob_segment(value: str) -> bool:
    if value in {".", ".."}:
        return False

    return _SAFE_SOURCE_BLOB_SEGMENT_PATTERN.fullmatch(value) is not None


def _is_safe_checksum(value: str) -> bool:
    return _SAFE_CHECKSUM_PATTERN.fullmatch(value) is not None


def _is_safe_artifact_version(value: str) -> bool:
    return _SAFE_ARTIFACT_VERSION_PATTERN.fullmatch(value) is not None
