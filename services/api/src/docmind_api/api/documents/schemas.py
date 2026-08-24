"""HTTP schemas for document registry endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from docmind_api.domain.attributes.models import (
    AttributeDataType,
    AttributeStatus,
    AttributeValueSource,
)
from docmind_api.domain.document_types.models import (
    DOCUMENT_TYPE_ID_MAX_LENGTH,
    DocumentTypeStatus,
)
from docmind_api.domain.documents.deletion import (
    DocumentDeletionFailureStage,
    DocumentDeletionStage,
    DocumentDeletionState,
)
from docmind_api.domain.documents.metadata import JsonScalar
from docmind_api.domain.documents.models import (
    DOCUMENT_CONNECTOR_INSTANCE_ID_MAX_LENGTH,
    DOCUMENT_CONNECTOR_MAX_LENGTH,
    DOCUMENT_CORRELATION_ID_MAX_LENGTH,
    DOCUMENT_EXTERNAL_ID_MAX_LENGTH,
    DOCUMENT_NAME_MAX_LENGTH,
    DOCUMENT_ORIGINAL_FILENAME_MAX_LENGTH,
    DOCUMENT_SOURCE_MAX_LENGTH,
    DocumentStatus,
)
from docmind_core.connectors import (
    ConnectorDocumentDeletionPolicy,
    ConnectorDocumentDeletionPreparationStatus,
)


class IngestDocumentRequest(BaseModel):
    """HTTP request schema for accepting a connector document."""

    model_config = ConfigDict(extra="forbid")

    original_filename: str = Field(max_length=DOCUMENT_ORIGINAL_FILENAME_MAX_LENGTH)
    document_type_id: str = Field(max_length=DOCUMENT_TYPE_ID_MAX_LENGTH)
    source: str = Field(max_length=DOCUMENT_SOURCE_MAX_LENGTH)
    connector: str = Field(max_length=DOCUMENT_CONNECTOR_MAX_LENGTH)
    connector_instance_id: str = Field(max_length=DOCUMENT_CONNECTOR_INSTANCE_ID_MAX_LENGTH)
    content_base64: str
    metadata_values: dict[str, Any] = Field(default_factory=dict)
    name: str | None = Field(default=None, max_length=DOCUMENT_NAME_MAX_LENGTH)
    external_id: str | None = Field(default=None, max_length=DOCUMENT_EXTERNAL_ID_MAX_LENGTH)
    connector_correlation_id: str | None = Field(
        default=None,
        max_length=DOCUMENT_CORRELATION_ID_MAX_LENGTH,
    )
    content_type: str | None = Field(default=None, max_length=255)


class DocumentUploadActorSchema(BaseModel):
    """Audit-safe user metadata for a browser manual upload."""

    user_id: str
    display_name: str


class DocumentSchema(BaseModel):
    """HTTP schema for a document registry entry."""

    id: UUID
    external_id: str | None
    name: str
    original_filename: str
    document_type_id: UUID
    status: DocumentStatus
    source: str
    connector: str
    connector_instance_id: str | None
    connector_correlation_id: str | None
    storage_locator: str
    content_size_bytes: int | None
    metadata_values: dict[str, JsonScalar]
    created_at: datetime
    updated_at: datetime
    uploaded_by: DocumentUploadActorSchema | None = None


class DocumentEnvelope(BaseModel):
    """Standard API response envelope for one document."""

    data: DocumentSchema
    meta: dict[str, str] = Field(default_factory=dict)


class DocumentDeletionOperationSchema(BaseModel):
    """Payload-free durable deletion status."""

    operation_id: UUID
    document_id: UUID
    stage: DocumentDeletionStage
    state: DocumentDeletionState
    policy: ConnectorDocumentDeletionPolicy | None
    warning_code: str | None
    failure_stage: DocumentDeletionFailureStage | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class DocumentDeletionImpactSchema(BaseModel):
    """Safe impact shown before destructive confirmation."""

    document_id: UUID
    policy: ConnectorDocumentDeletionPolicy
    preparation_status: ConnectorDocumentDeletionPreparationStatus
    warning_code: str | None
    error_code: str | None
    preserved_artifact_labels: list[str]
    operation: DocumentDeletionOperationSchema | None


class DocumentDeletionImpactEnvelope(BaseModel):
    data: DocumentDeletionImpactSchema
    meta: dict[str, str] = Field(default_factory=dict)


class DocumentDeletionEnvelope(BaseModel):
    data: DocumentDeletionOperationSchema
    meta: dict[str, str] = Field(default_factory=dict)


class ChangeDocumentTypeRequest(BaseModel):
    """Reviewer request to assign a configured document type."""

    model_config = ConfigDict(extra="forbid")

    document_type_id: UUID
    reason: str | None = Field(default=None, max_length=2000)
    confirm_impact: bool = False


class DocumentTypeChangeImpactSchema(BaseModel):
    requires_confirmation: bool
    added_fields: list[str]
    removed_fields: list[str]
    requiredness_changed_fields: list[str]
    reprocessing_requested: bool


class DocumentTypeChangeDocumentSchema(BaseModel):
    """Safe document projection returned after a reviewer changes its type."""

    id: UUID
    external_id: str | None
    name: str
    original_filename: str
    document_type_id: UUID
    status: DocumentStatus
    source: str
    connector: str
    connector_instance_id: str | None
    connector_correlation_id: str | None
    content_size_bytes: int | None
    metadata_values: dict[str, JsonScalar]
    created_at: datetime
    updated_at: datetime
    uploaded_by: DocumentUploadActorSchema | None = None


class DocumentTypeChangeSchema(BaseModel):
    document: DocumentTypeChangeDocumentSchema
    impact: DocumentTypeChangeImpactSchema


class DocumentTypeChangeEnvelope(BaseModel):
    data: DocumentTypeChangeSchema
    meta: dict[str, str] = Field(default_factory=dict)


class DocumentDetailSchema(BaseModel):
    """HTTP schema for a document preview detail view."""

    id: UUID
    external_id: str | None
    name: str
    original_filename: str
    document_type_id: UUID
    document_type_external_id: str | None = None
    document_type_name: str
    status: DocumentStatus
    source: str
    connector: str
    connector_name: str
    connector_instance_id: str | None
    connector_correlation_id: str | None
    content_size_bytes: int | None
    metadata_values: dict[str, JsonScalar]
    created_at: datetime
    updated_at: datetime
    uploaded_by: DocumentUploadActorSchema | None = None
    archive_url: str | None = None


class DocumentDetailEnvelope(BaseModel):
    """Standard API response envelope for one document detail view."""

    data: DocumentDetailSchema
    meta: dict[str, str] = Field(default_factory=dict)


class DocumentListItemSchema(BaseModel):
    """HTTP schema for a document registry list row."""

    id: UUID
    name: str
    original_filename: str
    document_type_id: UUID
    document_type_external_id: str | None = None
    document_type_name: str
    status: DocumentStatus
    source: str
    connector: str
    connector_name: str
    connector_instance_id: str | None
    connector_correlation_id: str | None
    content_size_bytes: int | None
    created_at: datetime
    updated_at: datetime
    uploaded_by: DocumentUploadActorSchema | None = None
    archive_url: str | None = None


class DocumentListSchema(BaseModel):
    """HTTP schema for document registry collections."""

    documents: list[DocumentListItemSchema]


class DocumentListMetaSchema(BaseModel):
    """HTTP metadata for document registry collections."""

    returned_count: int
    source: str | None
    limit: int
    offset: int
    has_more: bool


class DocumentListEnvelope(BaseModel):
    """Standard API response envelope for listed documents."""

    data: DocumentListSchema
    meta: DocumentListMetaSchema


class ManualUploadDocumentTypeSchema(BaseModel):
    """Document type available for manual Inbox uploads."""

    id: UUID
    external_id: str | None
    name: str


class ManualUploadOptionsSchema(BaseModel):
    """Upload options needed by the browser Inbox."""

    document_types: list[ManualUploadDocumentTypeSchema]


class ManualUploadOptionsMetaSchema(BaseModel):
    """HTTP metadata for manual upload options."""

    returned_count: int


class ManualUploadOptionsEnvelope(BaseModel):
    """Standard API response envelope for manual upload options."""

    data: ManualUploadOptionsSchema
    meta: ManualUploadOptionsMetaSchema


class ManualUploadMetadataFieldSchema(BaseModel):
    """Metadata field collected during browser manual upload."""

    id: UUID
    external_id: str | None
    key: str
    label: str
    category: str
    category_id: UUID
    data_type: AttributeDataType
    required: bool
    constraints: dict[str, int | float | str]
    allowed_values: list[str]
    value_source: AttributeValueSource
    dictionary_id: UUID | None
    status: AttributeStatus
    schema_version: int


class ManualUploadMetadataDocumentTypeSchema(BaseModel):
    """Document type summary for a manual upload metadata schema."""

    id: UUID
    external_id: str | None
    name: str
    status: DocumentTypeStatus


class ManualUploadMetadataSchemaPayload(BaseModel):
    """Manual upload metadata schema payload."""

    document_type: ManualUploadMetadataDocumentTypeSchema
    fields: list[ManualUploadMetadataFieldSchema]


class ManualUploadMetadataSchemaMeta(BaseModel):
    """Counters for the manual upload metadata schema."""

    document_type_id: UUID
    field_count: int
    required_field_count: int


class ManualUploadMetadataSchemaEnvelope(BaseModel):
    """Standard API response envelope for manual upload metadata schema."""

    data: ManualUploadMetadataSchemaPayload
    meta: ManualUploadMetadataSchemaMeta
