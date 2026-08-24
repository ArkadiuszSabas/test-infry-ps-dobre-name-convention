"""Application commands for the document registry."""

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from docmind_api.domain.documents.models import DocumentUploadActor


@dataclass(frozen=True, slots=True)
class IngestDocumentCommand:
    """Input for accepting a document from a connector."""

    original_filename: str
    document_type_id: UUID | str
    source: str
    connector: str
    connector_instance_id: str
    content: bytes
    metadata_values: Mapping[str, object]
    name: str | None = None
    external_id: str | None = None
    connector_correlation_id: str | None = None
    content_type: str | None = None


@dataclass(frozen=True, slots=True)
class ManualUploadDocumentCommand:
    """Input for accepting a PDF uploaded through the browser Inbox."""

    original_filename: str
    document_type_id: UUID | str
    content: bytes
    content_type: str | None
    uploaded_by: DocumentUploadActor
    metadata_values: Mapping[str, object]
    name: str | None = None


@dataclass(frozen=True, slots=True)
class ChangeDocumentTypeCommand:
    """Input for a reviewer-approved document type reassignment."""

    document_id: UUID
    document_type_id: UUID | str
    actor_id: str
    reason: str | None = None
    confirm_impact: bool = False
