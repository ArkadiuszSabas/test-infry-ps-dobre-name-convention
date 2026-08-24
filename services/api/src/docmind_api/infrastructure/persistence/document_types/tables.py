"""SQLAlchemy table definitions for document type catalog persistence."""

from sqlalchemy import CheckConstraint, Column, DateTime, Index, String, Table
from sqlalchemy.dialects.postgresql import UUID

from docmind_api.domain.document_types.models import (
    DOCUMENT_TYPE_DESCRIPTION_MAX_LENGTH,
    DOCUMENT_TYPE_ID_MAX_LENGTH,
)
from docmind_api.infrastructure.persistence.metadata import metadata

document_types_table = Table(
    "document_types",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("external_id", String(length=DOCUMENT_TYPE_ID_MAX_LENGTH), nullable=True),
    Column("name", String(length=200), nullable=False),
    Column("description", String(length=DOCUMENT_TYPE_DESCRIPTION_MAX_LENGTH), nullable=True),
    Column("status", String(length=32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "external_id is null or length(trim(external_id)) > 0",
        name="external_id_not_empty",
    ),
    CheckConstraint(
        "length(trim(name)) > 0",
        name="name_not_empty",
    ),
    CheckConstraint(
        "description is null or length(trim(description)) > 0",
        name="description_not_empty",
    ),
    CheckConstraint(
        "status in ('active', 'inactive')",
        name="status_supported",
    ),
    CheckConstraint(
        "created_at <= updated_at",
        name="updated_at_not_before_created_at",
    ),
    Index("ix_document_types_status", "status"),
    Index("uq_document_types_external_id", "external_id", unique=True),
)
