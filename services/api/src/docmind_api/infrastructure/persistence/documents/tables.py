"""SQLAlchemy table definitions for document registry persistence."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from docmind_api.domain.documents.models import (
    DOCUMENT_CONNECTOR_INSTANCE_ID_MAX_LENGTH,
    DOCUMENT_CONNECTOR_MAX_LENGTH,
    DOCUMENT_CORRELATION_ID_MAX_LENGTH,
    DOCUMENT_EXTERNAL_ID_MAX_LENGTH,
    DOCUMENT_NAME_MAX_LENGTH,
    DOCUMENT_ORIGINAL_FILENAME_MAX_LENGTH,
    DOCUMENT_SOURCE_MAX_LENGTH,
    DOCUMENT_STORAGE_LOCATOR_MAX_LENGTH,
    DOCUMENT_UPLOAD_ACTOR_DISPLAY_NAME_MAX_LENGTH,
    DOCUMENT_UPLOAD_ACTOR_USER_ID_MAX_LENGTH,
)
from docmind_api.infrastructure.persistence.metadata import metadata

documents_table = Table(
    "documents",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("external_id", String(length=DOCUMENT_EXTERNAL_ID_MAX_LENGTH), nullable=True),
    Column("name", String(length=DOCUMENT_NAME_MAX_LENGTH), nullable=False),
    Column(
        "original_filename",
        String(length=DOCUMENT_ORIGINAL_FILENAME_MAX_LENGTH),
        nullable=False,
    ),
    Column(
        "document_type_id",
        UUID(as_uuid=True),
        ForeignKey("document_types.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("status", String(length=32), nullable=False),
    Column("source", String(length=DOCUMENT_SOURCE_MAX_LENGTH), nullable=False),
    Column("connector", String(length=DOCUMENT_CONNECTOR_MAX_LENGTH), nullable=False),
    Column(
        "connector_instance_id",
        String(length=DOCUMENT_CONNECTOR_INSTANCE_ID_MAX_LENGTH),
        nullable=True,
    ),
    Column(
        "connector_correlation_id",
        String(length=DOCUMENT_CORRELATION_ID_MAX_LENGTH),
        nullable=True,
    ),
    Column(
        "storage_locator",
        String(length=DOCUMENT_STORAGE_LOCATOR_MAX_LENGTH),
        nullable=False,
    ),
    Column("content_size_bytes", BigInteger, nullable=True),
    Column("metadata_values", JSONB, nullable=False),
    Column(
        "uploaded_by_user_id",
        String(length=DOCUMENT_UPLOAD_ACTOR_USER_ID_MAX_LENGTH),
        nullable=True,
    ),
    Column(
        "uploaded_by_display_name",
        String(length=DOCUMENT_UPLOAD_ACTOR_DISPLAY_NAME_MAX_LENGTH),
        nullable=True,
    ),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
    CheckConstraint(
        "external_id is null or length(trim(external_id)) > 0",
        name="external_id_not_empty",
    ),
    CheckConstraint(
        "length(trim(original_filename)) > 0",
        name="original_filename_not_empty",
    ),
    CheckConstraint(
        "status in ('received', 'waiting_for_review', 'in_review', 'approved')",
        name="status_supported",
    ),
    CheckConstraint("length(trim(source)) > 0", name="source_not_empty"),
    CheckConstraint("length(trim(connector)) > 0", name="connector_not_empty"),
    CheckConstraint(
        "connector_instance_id is null or length(trim(connector_instance_id)) > 0",
        name="connector_instance_id_not_empty",
    ),
    CheckConstraint(
        "connector_correlation_id is null or length(trim(connector_correlation_id)) > 0",
        name="connector_correlation_id_not_empty",
    ),
    CheckConstraint(
        "length(trim(storage_locator)) > 0",
        name="storage_locator_not_empty",
    ),
    CheckConstraint(
        "content_size_bytes is null or content_size_bytes >= 0",
        name="content_size_bytes_non_negative",
    ),
    CheckConstraint(
        "jsonb_typeof(metadata_values) = 'object'",
        name="metadata_values_object",
    ),
    CheckConstraint(
        "uploaded_by_user_id is null or length(trim(uploaded_by_user_id)) > 0",
        name="uploaded_by_user_id_not_empty",
    ),
    CheckConstraint(
        "uploaded_by_display_name is null or length(trim(uploaded_by_display_name)) > 0",
        name="uploaded_by_display_name_not_empty",
    ),
    CheckConstraint(
        "(uploaded_by_user_id is null and uploaded_by_display_name is null) "
        "or (uploaded_by_user_id is not null and uploaded_by_display_name is not null)",
        name="uploaded_by_complete",
    ),
    CheckConstraint(
        "created_at <= updated_at",
        name="updated_at_not_before_created_at",
    ),
    Index("ix_documents_document_type_id", "document_type_id"),
    Index("ix_documents_external_id", "external_id"),
    Index("ix_documents_status", "status"),
    Index("ix_documents_source", "source"),
    Index("ix_documents_connector", "connector"),
    Index("ix_documents_connector_instance_id", "connector_instance_id"),
    Index("ix_documents_connector_correlation_id", "connector_correlation_id"),
    Index("ix_documents_created_at", "created_at"),
    Index("ix_documents_status_updated_at", "status", "updated_at"),
)

document_type_change_audit_events_table = Table(
    "document_type_change_audit_events",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "old_document_type_id",
        UUID(as_uuid=True),
        ForeignKey("document_types.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "new_document_type_id",
        UUID(as_uuid=True),
        ForeignKey("document_types.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("actor_id", String(length=200), nullable=False),
    Column("reason", String(length=2000), nullable=True),
    Column("changed_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("length(trim(actor_id)) > 0", name="actor_id_not_empty"),
    Index("ix_document_type_change_audit_events_document_id", "document_id"),
)
