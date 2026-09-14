"""Read models for document registry list views."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from docmind_api.domain.attributes.models import (
    AttributeDataType,
    AttributeStatus,
    AttributeValueSource,
)
from docmind_api.domain.document_types.models import DocumentType
from docmind_api.domain.documents.models import DocumentRecord

DOCUMENT_LIST_DEFAULT_LIMIT = 50
DOCUMENT_LIST_MAX_LIMIT = 200


class DocumentListSortField(StrEnum):
    """Closed persistence sort fields for document registry collections."""

    CREATED = "created"
    NAME = "name"
    DOCUMENT_TYPE = "document_type"
    SOURCE = "source"
    STATUS = "status"
    SIZE = "size"


class DocumentListSortOrder(StrEnum):
    """Sort directions understood by the document registry repository."""

    ASC = "asc"
    DESC = "desc"


class DocumentListStatus(StrEnum):
    """Canonical processing status displayed and queried by document lists."""

    RECEIVED = "received"
    WAITING_FOR_REVIEW = "waiting_for_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class DocumentListQuery:
    """Framework-free document list criteria applied before pagination."""

    source: str | None
    connector: str | None
    archived: bool | None
    search: str | None
    status: DocumentListStatus | None
    document_type_id: UUID | None
    sort_by: DocumentListSortField
    sort_order: DocumentListSortOrder
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class DocumentListItem:
    """A registry document enriched for Inbox-style list views."""

    document: DocumentRecord
    document_type_name: str
    document_type_external_id: str | None
    connector_name: str
    status: DocumentListStatus
    archive_url: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentListEntry:
    """One persistence list row with its canonical OCR-aware status."""

    document: DocumentRecord
    status: DocumentListStatus


@dataclass(frozen=True, slots=True)
class DocumentDetail:
    """A registry document enriched for document preview and metadata views."""

    document: DocumentRecord
    document_type_name: str
    document_type_external_id: str | None
    connector_name: str
    archive_url: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentListResult:
    """Documents returned by a registry listing."""

    items: tuple[DocumentListItem, ...]
    source: str | None
    total_count: int
    status_counts: tuple[tuple[str, int], ...]
    document_type_counts: tuple[tuple[UUID, int], ...]
    limit: int
    offset: int
    has_more: bool

    @property
    def returned_count(self) -> int:
        """Return the number of listed documents."""

        return len(self.items)

    @property
    def documents(self) -> tuple[DocumentRecord, ...]:
        """Return the underlying document records."""

        return tuple(item.document for item in self.items)


@dataclass(frozen=True, slots=True)
class DocumentPdfPreview:
    """Application response for raw PDF preview content."""

    document: DocumentRecord
    content: bytes


@dataclass(frozen=True, slots=True)
class ManualUploadMetadataField:
    """A metadata field collected by the browser manual upload form."""

    id: UUID
    external_id: str | None
    key: str
    label: str
    category: str
    category_id: UUID
    data_type: AttributeDataType
    required: bool
    constraints: dict[str, int | float | str]
    allowed_values: tuple[str, ...]
    value_source: AttributeValueSource
    dictionary_id: UUID | None
    status: AttributeStatus
    schema_version: int


@dataclass(frozen=True, slots=True)
class ManualUploadMetadataSchema:
    """Metadata schema returned to the Inbox manual upload workflow."""

    document_type: DocumentType
    fields: tuple[ManualUploadMetadataField, ...]

    @property
    def field_count(self) -> int:
        """Return the number of returned metadata fields."""

        return len(self.fields)

    @property
    def required_field_count(self) -> int:
        """Return the number of required returned metadata fields."""

        return sum(1 for field in self.fields if field.required)
