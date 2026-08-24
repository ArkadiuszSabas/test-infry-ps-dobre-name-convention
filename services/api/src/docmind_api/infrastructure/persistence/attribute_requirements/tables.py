"""SQLAlchemy table definitions for document type attribute requirements."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from docmind_api.domain.attributes.models import ATTRIBUTE_ID_MAX_LENGTH
from docmind_api.infrastructure.persistence.metadata import metadata

attribute_requirements_table = Table(
    "attribute_requirements",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("external_id", String(length=ATTRIBUTE_ID_MAX_LENGTH), nullable=False),
    Column(
        "document_type_id",
        UUID(as_uuid=True),
        ForeignKey("document_types.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "attribute_definition_id",
        UUID(as_uuid=True),
        ForeignKey("attribute_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("required", Boolean, nullable=False),
    Column(
        "include_metadata_in_context_resolver",
        Boolean,
        nullable=False,
        server_default="false",
    ),
    Column("missing_required_action", String(length=64), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "external_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
        name="external_id_snake_case",
    ),
    CheckConstraint(
        "missing_required_action in ('block_approval', 'require_review')",
        name="missing_required_action_supported",
    ),
    CheckConstraint(
        "("
        "required = true "
        "and missing_required_action in ('block_approval', 'require_review')"
        ") or (required = false and missing_required_action is null)",
        name="missing_required_action_matches_required",
    ),
    CheckConstraint(
        "created_at <= updated_at",
        name="updated_at_not_before_created_at",
    ),
    UniqueConstraint(
        "document_type_id",
        "attribute_definition_id",
        name="uq_attribute_requirements_document_type_attribute_definition",
    ),
    Index("uq_attribute_requirements_external_id", "external_id", unique=True),
    Index("ix_attribute_requirements_document_type_id", "document_type_id"),
    Index("ix_attribute_requirements_attribute_definition_id", "attribute_definition_id"),
)
