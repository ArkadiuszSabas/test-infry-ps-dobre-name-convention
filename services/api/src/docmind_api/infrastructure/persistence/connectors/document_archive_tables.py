"""SQLAlchemy table for neutral connector approved-document archive state."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.dialects.postgresql import UUID

from docmind_api.infrastructure.persistence.metadata import metadata

connector_document_archives_table = Table(
    "connector_document_archives",
    metadata,
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    ),
    Column("connector_instance_id", String(length=200), nullable=False),
    Column("handler_id", String(length=160), nullable=False),
    Column("review_version", Integer, nullable=False),
    Column("status", String(length=20), nullable=False),
    Column("approved_at", DateTime(timezone=True), nullable=False),
    Column("folder_path", String(length=1024), nullable=False),
    Column("file_name", String(length=255), nullable=False),
    Column("drive_item_id", String(length=512), nullable=True),
    Column("web_url", String(length=2048), nullable=True),
    Column("error_code", String(length=80), nullable=True),
    Column("failure_stage", String(length=20), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("length(trim(connector_instance_id)) > 0", name="instance_id_not_empty"),
    CheckConstraint("length(trim(handler_id)) > 0", name="handler_id_not_empty"),
    CheckConstraint("review_version > 0", name="review_version_positive"),
    CheckConstraint(
        "status in ('pending', 'succeeded', 'failed', 'cancelled')",
        name="status_supported",
    ),
    CheckConstraint("length(trim(folder_path)) > 0", name="folder_path_not_empty"),
    CheckConstraint("length(trim(file_name)) > 0", name="file_name_not_empty"),
    CheckConstraint(
        "(status = 'pending' and drive_item_id is null and web_url is null "
        "and error_code is null and failure_stage is null) "
        "or (status = 'succeeded' and drive_item_id is not null and web_url is not null "
        "and error_code is null and failure_stage is null) "
        "or (status = 'failed' and drive_item_id is null and web_url is null "
        "and error_code is not null and failure_stage in ('preflight', 'io')) "
        "or (status = 'cancelled' and drive_item_id is null and web_url is null "
        "and error_code is not null and failure_stage is null)",
        name="terminal_fields_match_status",
    ),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
)
