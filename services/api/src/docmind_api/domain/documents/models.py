"""Document registry domain models."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from uuid import NAMESPACE_URL, UUID, uuid5

from docmind_api.domain.documents.metadata import JsonScalar

DOCUMENT_CONNECTOR_MAX_LENGTH = 120
DOCUMENT_CONNECTOR_INSTANCE_ID_MAX_LENGTH = 200
DOCUMENT_CORRELATION_ID_MAX_LENGTH = 200
DOCUMENT_EXTERNAL_ID_MAX_LENGTH = 200
DOCUMENT_NAME_MAX_LENGTH = 255
DOCUMENT_ORIGINAL_FILENAME_MAX_LENGTH = 255
DOCUMENT_SOURCE_MAX_LENGTH = 120
DOCUMENT_STORAGE_LOCATOR_MAX_LENGTH = 2048
DOCUMENT_UPLOAD_ACTOR_DISPLAY_NAME_MAX_LENGTH = 320
DOCUMENT_UPLOAD_ACTOR_USER_ID_MAX_LENGTH = 200
MANUAL_UPLOAD_CONNECTOR = "manual_upload"
MANUAL_UPLOAD_CONNECTOR_INSTANCE_ID = "core.manual_upload.primary"
MANUAL_UPLOAD_SOURCE = "manual_upload"


class DocumentStatus(StrEnum):
    """Lifecycle status for an accepted document."""

    RECEIVED = "received"
    WAITING_FOR_REVIEW = "waiting_for_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"


class DocumentMetadataState(StrEnum):
    """Metadata completion state derived from document source and values."""

    COMPLETE = "complete"
    PENDING_EXTRACTION = "pending_extraction"


@dataclass(frozen=True, slots=True)
class StorageLocator:
    """Stable locator returned by object storage for the raw document content."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _normalize_required_text(
                self.value,
                field_name="Storage locator",
                max_length=DOCUMENT_STORAGE_LOCATOR_MAX_LENGTH,
            ),
        )


@dataclass(frozen=True, slots=True)
class DocumentSource:
    """Connector source metadata attached to an ingested document."""

    source: str
    connector: str
    connector_instance_id: str | None = None
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source",
            _normalize_required_text(
                self.source,
                field_name="Document source",
                max_length=DOCUMENT_SOURCE_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "connector",
            _normalize_required_text(
                self.connector,
                field_name="Document connector",
                max_length=DOCUMENT_CONNECTOR_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "connector_instance_id",
            _normalize_optional_text(
                self.connector_instance_id,
                field_name="Connector instance ID",
                max_length=DOCUMENT_CONNECTOR_INSTANCE_ID_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "correlation_id",
            _normalize_optional_text(
                self.correlation_id,
                field_name="Document correlation ID",
                max_length=DOCUMENT_CORRELATION_ID_MAX_LENGTH,
            ),
        )


@dataclass(frozen=True, slots=True)
class DocumentUploadActor:
    """Audit-safe actor metadata for browser manual uploads."""

    user_id: str
    display_name: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "user_id",
            _normalize_required_text(
                self.user_id,
                field_name="Upload actor user ID",
                max_length=DOCUMENT_UPLOAD_ACTOR_USER_ID_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "display_name",
            _normalize_required_text(
                self.display_name,
                field_name="Upload actor display name",
                max_length=DOCUMENT_UPLOAD_ACTOR_DISPLAY_NAME_MAX_LENGTH,
            ),
        )


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """A document accepted into the API-owned registry."""

    id: UUID
    name: str
    original_filename: str
    document_type_id: UUID | str
    status: DocumentStatus
    source: DocumentSource
    storage_locator: StorageLocator
    content_size_bytes: int | None
    metadata_values: Mapping[str, JsonScalar]
    created_at: datetime
    updated_at: datetime
    external_id: str | None = None
    uploaded_by: DocumentUploadActor | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "external_id",
            _normalize_optional_text(
                self.external_id,
                field_name="Document external_id",
                max_length=DOCUMENT_EXTERNAL_ID_MAX_LENGTH,
            ),
        )
        object.__setattr__(
            self,
            "name",
            normalize_document_name(self.name),
        )
        object.__setattr__(
            self,
            "original_filename",
            normalize_document_original_filename(self.original_filename),
        )
        object.__setattr__(
            self,
            "document_type_id",
            _normalize_document_type_reference(self.document_type_id),
        )
        object.__setattr__(
            self,
            "metadata_values",
            MappingProxyType(dict(self.metadata_values)),
        )
        if self.content_size_bytes is not None and self.content_size_bytes < 0:
            raise ValueError("Document content size cannot be negative.")
        if self.created_at > self.updated_at:
            raise ValueError("Document updated_at cannot be before created_at.")

    @property
    def metadata_state(self) -> DocumentMetadataState:
        """Return whether selected-type metadata is complete or awaiting extraction."""

        if (
            self.source.source == MANUAL_UPLOAD_SOURCE
            and self.source.connector == MANUAL_UPLOAD_CONNECTOR
            and not self.metadata_values
        ):
            return DocumentMetadataState.PENDING_EXTRACTION

        return DocumentMetadataState.COMPLETE


def normalize_document_name(value: str) -> str:
    """Validate and return a document display name."""

    return _normalize_required_text(
        value,
        field_name="Document name",
        max_length=DOCUMENT_NAME_MAX_LENGTH,
    )


def normalize_document_original_filename(value: str) -> str:
    """Validate and return the original filename supplied by the connector."""

    return _normalize_required_text(
        value,
        field_name="Original filename",
        max_length=DOCUMENT_ORIGINAL_FILENAME_MAX_LENGTH,
    )


def _normalize_document_type_reference(value: UUID | str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError:
        return uuid5(NAMESPACE_URL, f"docmind:document-type:{value}")


def _normalize_required_text(value: str, *, field_name: str, max_length: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters.")

    return normalized


def _normalize_optional_text(
    value: str | None,
    *,
    field_name: str,
    max_length: int,
) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters.")

    return normalized
