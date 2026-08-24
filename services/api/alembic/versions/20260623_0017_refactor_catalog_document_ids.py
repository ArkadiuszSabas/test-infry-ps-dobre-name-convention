"""Refactor catalog and document identifiers.

Revision ID: 20260623_0017
Revises: 20260616_0016
Create Date: 2026-06-23 18:30:00.000000
"""

import os
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260623_0017"
down_revision: str | None = "20260616_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BUSINESS_ID_MAX_LENGTH = 80
COMMENT_MAX_LENGTH = 2000
ALLOWED_VALUE_MAX_LENGTH = 200
SCOPED_TABLES = (
    "document_types",
    "attribute_definitions",
    "attribute_requirements",
    "documents",
)
DESTRUCTIVE_MIGRATION_APPROVAL_ENV = "DOCMIND_ID_REFACTOR_ALLOW_DESTRUCTIVE_MIGRATION"


def upgrade() -> None:
    """Rebuild the scoped tables with UUID technical IDs and external business IDs."""

    _guard_empty_scoped_tables(op.get_bind())
    _drop_scoped_tables()
    _create_document_types_uuid()
    _create_attribute_definitions_uuid()
    _create_attribute_requirements_uuid()
    _create_documents_uuid()


def downgrade() -> None:
    """Restore the previous scoped table shape."""

    _guard_empty_scoped_tables(op.get_bind())
    _drop_scoped_tables()
    _create_document_types_legacy()
    _create_attribute_definitions_legacy()
    _create_attribute_requirements_legacy()
    _create_documents_legacy()


def _drop_scoped_tables() -> None:
    op.drop_table("documents")
    op.drop_table("attribute_requirements")
    op.drop_table("attribute_definitions")
    op.drop_table("document_types")


def _guard_destructive_migration_release_approval() -> None:
    if os.environ.get(DESTRUCTIVE_MIGRATION_APPROVAL_ENV) == "true":
        return

    raise RuntimeError(
        "Refusing to run destructive identifier refactor migration without explicit release "
        f"approval. Set {DESTRUCTIVE_MIGRATION_APPROVAL_ENV}=true only for an approved "
        "disposable-environment rollout after clearing documents, attribute_requirements, "
        "attribute_definitions, and document_types. Use a data-preserving backfill migration "
        "for non-disposable environments.",
    )


def _guard_empty_scoped_tables(connection: Any) -> None:
    non_empty_tables: list[str] = []
    for table_name in SCOPED_TABLES:
        row_count = int(connection.scalar(sa.text(f"select count(*) from {table_name}")) or 0)
        if row_count:
            non_empty_tables.append(f"{table_name}={row_count}")

    if non_empty_tables:
        raise RuntimeError(
            "Refusing to run destructive identifier refactor migration while scoped tables "
            f"contain rows: {', '.join(non_empty_tables)}. Clear disposable local data with "
            "services/api/scripts/clear-id-refactor-data.ps1 or ship a data-preserving "
            "backfill migration for non-disposable environments.",
        )


def _create_document_types_uuid() -> None:
    op.create_table(
        "document_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=BUSINESS_ID_MAX_LENGTH), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=COMMENT_MAX_LENGTH), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "external_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
            name=op.f("ck_document_types_external_id_snake_case"),
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_document_types_name_not_empty")),
        sa.CheckConstraint(
            "description is null or length(trim(description)) > 0",
            name=op.f("ck_document_types_description_not_empty"),
        ),
        sa.CheckConstraint(
            "status in ('active', 'inactive')",
            name=op.f("ck_document_types_status_supported"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_document_types_updated_at_not_before_created_at"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_types")),
    )
    op.create_index(op.f("ix_document_types_status"), "document_types", ["status"])
    op.create_index(
        op.f("uq_document_types_external_id"),
        "document_types",
        ["external_id"],
        unique=True,
    )


def _create_attribute_definitions_uuid() -> None:
    op.create_table(
        "attribute_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=BUSINESS_ID_MAX_LENGTH), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("data_type", sa.String(length=32), nullable=False),
        sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("allowed_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.String(length=COMMENT_MAX_LENGTH), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "external_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
            name=op.f("ck_attribute_definitions_external_id_snake_case"),
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name=op.f("ck_attribute_definitions_name_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(category)) > 0",
            name=op.f("ck_attribute_definitions_category_not_empty"),
        ),
        sa.CheckConstraint(
            "data_type in ("
            "'legacy_scalar', 'string', 'integer', 'number', 'boolean', 'date', 'datetime'"
            ")",
            name=op.f("ck_attribute_definitions_data_type_supported"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(constraints) = 'object'",
            name=op.f("ck_attribute_definitions_constraints_object"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(allowed_values) = 'array'",
            name=op.f("ck_attribute_definitions_allowed_values_array"),
        ),
        sa.CheckConstraint(
            f"jsonb_text_array_is_valid(allowed_values, {ALLOWED_VALUE_MAX_LENGTH})",
            name=op.f("ck_attribute_definitions_allowed_values_entries_valid"),
        ),
        sa.CheckConstraint(
            "data_type in ('legacy_scalar', 'string') or jsonb_array_length(allowed_values) = 0",
            name=op.f("ck_attribute_definitions_allowed_values_match_data_type"),
        ),
        sa.CheckConstraint(
            "source in ('ai', 'user')",
            name=op.f("ck_attribute_definitions_source_supported"),
        ),
        sa.CheckConstraint(
            "comment is null or length(trim(comment)) > 0",
            name=op.f("ck_attribute_definitions_comment_not_empty"),
        ),
        sa.CheckConstraint(
            "status in ('active', 'inactive')",
            name=op.f("ck_attribute_definitions_status_supported"),
        ),
        sa.CheckConstraint(
            "schema_version > 0",
            name=op.f("ck_attribute_definitions_schema_version_positive"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_attribute_definitions_updated_at_not_before_created_at"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attribute_definitions")),
    )
    op.create_index(
        op.f("ix_attribute_definitions_category"),
        "attribute_definitions",
        ["category"],
    )
    op.create_index(
        op.f("ix_attribute_definitions_status"),
        "attribute_definitions",
        ["status"],
    )
    op.create_index(
        op.f("uq_attribute_definitions_external_id"),
        "attribute_definitions",
        ["external_id"],
        unique=True,
    )


def _create_attribute_requirements_uuid() -> None:
    op.create_table(
        "attribute_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=BUSINESS_ID_MAX_LENGTH), nullable=False),
        sa.Column("document_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attribute_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("missing_required_action", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attribute_definition_id"],
            ["attribute_definitions.id"],
            name=op.f("fk_attribute_requirements_attribute_definition_id_attribute_definitions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_type_id"],
            ["document_types.id"],
            name=op.f("fk_attribute_requirements_document_type_id_document_types"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "external_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
            name=op.f("ck_attribute_requirements_external_id_snake_case"),
        ),
        sa.CheckConstraint(
            "missing_required_action in ('block_approval', 'require_review')",
            name=op.f("ck_attribute_requirements_missing_required_action_supported"),
        ),
        sa.CheckConstraint(
            "(required = true and missing_required_action in ('block_approval', 'require_review')) "
            "or (required = false and missing_required_action is null)",
            name=op.f("ck_attribute_requirements_missing_required_action_matches_required"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_attribute_requirements_updated_at_not_before_created_at"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attribute_requirements")),
        sa.UniqueConstraint(
            "document_type_id",
            "attribute_definition_id",
            name=op.f("uq_attribute_requirements_document_type_attribute_definition"),
        ),
    )
    op.create_index(
        op.f("uq_attribute_requirements_external_id"),
        "attribute_requirements",
        ["external_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_attribute_requirements_document_type_id"),
        "attribute_requirements",
        ["document_type_id"],
    )
    op.create_index(
        op.f("ix_attribute_requirements_attribute_definition_id"),
        "attribute_requirements",
        ["attribute_definition_id"],
    )


def _create_documents_uuid() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("document_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("connector", sa.String(length=120), nullable=False),
        sa.Column("connector_correlation_id", sa.String(length=200), nullable=True),
        sa.Column("storage_locator", sa.String(length=2048), nullable=False),
        sa.Column("content_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("metadata_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_type_id"],
            ["document_types.id"],
            name=op.f("fk_documents_document_type_id_document_types"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_documents_name_not_empty")),
        sa.CheckConstraint(
            "external_id is null or length(trim(external_id)) > 0",
            name=op.f("ck_documents_external_id_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(original_filename)) > 0",
            name=op.f("ck_documents_original_filename_not_empty"),
        ),
        sa.CheckConstraint("status in ('received')", name=op.f("ck_documents_status_supported")),
        sa.CheckConstraint(
            "length(trim(source)) > 0",
            name=op.f("ck_documents_source_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(connector)) > 0",
            name=op.f("ck_documents_connector_not_empty"),
        ),
        sa.CheckConstraint(
            "connector_correlation_id is null or length(trim(connector_correlation_id)) > 0",
            name=op.f("ck_documents_connector_correlation_id_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(storage_locator)) > 0",
            name=op.f("ck_documents_storage_locator_not_empty"),
        ),
        sa.CheckConstraint(
            "content_size_bytes is null or content_size_bytes >= 0",
            name=op.f("ck_documents_content_size_bytes_non_negative"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metadata_values) = 'object'",
            name=op.f("ck_documents_metadata_values_object"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_documents_updated_at_not_before_created_at"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(op.f("ix_documents_document_type_id"), "documents", ["document_type_id"])
    op.create_index(op.f("ix_documents_external_id"), "documents", ["external_id"])
    op.create_index(op.f("ix_documents_status"), "documents", ["status"])
    op.create_index(op.f("ix_documents_source"), "documents", ["source"])
    op.create_index(op.f("ix_documents_connector"), "documents", ["connector"])
    op.create_index(
        op.f("ix_documents_connector_correlation_id"),
        "documents",
        ["connector_correlation_id"],
    )


def _create_document_types_legacy() -> None:
    op.create_table(
        "document_types",
        sa.Column("id", sa.String(length=BUSINESS_ID_MAX_LENGTH), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=COMMENT_MAX_LENGTH), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
            name=op.f("ck_document_types_id_snake_case"),
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_document_types_name_not_empty")),
        sa.CheckConstraint(
            "description is null or length(trim(description)) > 0",
            name=op.f("ck_document_types_description_not_empty"),
        ),
        sa.CheckConstraint(
            "status in ('active', 'inactive')",
            name=op.f("ck_document_types_status_supported"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_document_types_updated_at_not_before_created_at"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_types")),
    )
    op.create_index(op.f("ix_document_types_status"), "document_types", ["status"])


def _create_attribute_definitions_legacy() -> None:
    op.create_table(
        "attribute_definitions",
        sa.Column("id", sa.String(length=BUSINESS_ID_MAX_LENGTH), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("allowed_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.String(length=COMMENT_MAX_LENGTH), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_type", sa.String(length=32), nullable=False),
        sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
            name=op.f("ck_attribute_definitions_id_snake_case"),
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name=op.f("ck_attribute_definitions_name_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(category)) > 0",
            name=op.f("ck_attribute_definitions_category_not_empty"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(allowed_values) = 'array'",
            name=op.f("ck_attribute_definitions_allowed_values_array"),
        ),
        sa.CheckConstraint(
            f"jsonb_text_array_is_valid(allowed_values, {ALLOWED_VALUE_MAX_LENGTH})",
            name=op.f("ck_attribute_definitions_allowed_values_entries_valid"),
        ),
        sa.CheckConstraint(
            "source in ('ai', 'user')",
            name=op.f("ck_attribute_definitions_source_supported"),
        ),
        sa.CheckConstraint(
            "comment is null or length(trim(comment)) > 0",
            name=op.f("ck_attribute_definitions_comment_not_empty"),
        ),
        sa.CheckConstraint(
            "status in ('active', 'inactive')",
            name=op.f("ck_attribute_definitions_status_supported"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_attribute_definitions_updated_at_not_before_created_at"),
        ),
        sa.CheckConstraint(
            "data_type in ("
            "'legacy_scalar', 'string', 'integer', 'number', 'boolean', 'date', 'datetime'"
            ")",
            name=op.f("ck_attribute_definitions_data_type_supported"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(constraints) = 'object'",
            name=op.f("ck_attribute_definitions_constraints_object"),
        ),
        sa.CheckConstraint(
            "data_type in ('legacy_scalar', 'string') or jsonb_array_length(allowed_values) = 0",
            name=op.f("ck_attribute_definitions_allowed_values_match_data_type"),
        ),
        sa.CheckConstraint(
            "schema_version > 0",
            name=op.f("ck_attribute_definitions_schema_version_positive"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attribute_definitions")),
    )
    op.create_index(
        op.f("ix_attribute_definitions_category"),
        "attribute_definitions",
        ["category"],
    )
    op.create_index(op.f("ix_attribute_definitions_status"), "attribute_definitions", ["status"])


def _create_attribute_requirements_legacy() -> None:
    op.create_table(
        "attribute_requirements",
        sa.Column("document_type_id", sa.String(length=BUSINESS_ID_MAX_LENGTH), nullable=False),
        sa.Column("attribute_id", sa.String(length=BUSINESS_ID_MAX_LENGTH), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("missing_required_action", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attribute_id"],
            ["attribute_definitions.id"],
            name=op.f("fk_attribute_requirements_attribute_id_attribute_definitions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_type_id"],
            ["document_types.id"],
            name=op.f("fk_attribute_requirements_document_type_id_document_types"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "document_type_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
            name=op.f("ck_attribute_requirements_document_type_id_snake_case"),
        ),
        sa.CheckConstraint(
            "attribute_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
            name=op.f("ck_attribute_requirements_attribute_id_snake_case"),
        ),
        sa.CheckConstraint(
            "missing_required_action in ('block_approval', 'require_review')",
            name=op.f("ck_attribute_requirements_missing_required_action_supported"),
        ),
        sa.CheckConstraint(
            "(required = true and missing_required_action in ('block_approval', 'require_review')) "
            "or (required = false and missing_required_action is null)",
            name=op.f("ck_attribute_requirements_missing_required_action_matches_required"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_attribute_requirements_updated_at_not_before_created_at"),
        ),
        sa.PrimaryKeyConstraint(
            "document_type_id",
            "attribute_id",
            name=op.f("pk_attribute_requirements"),
        ),
    )
    op.create_index(
        op.f("ix_attribute_requirements_attribute_id"),
        "attribute_requirements",
        ["attribute_id"],
    )


def _create_documents_legacy() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("document_type_id", sa.String(length=BUSINESS_ID_MAX_LENGTH), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("connector", sa.String(length=120), nullable=False),
        sa.Column("connector_correlation_id", sa.String(length=200), nullable=True),
        sa.Column("storage_locator", sa.String(length=2048), nullable=False),
        sa.Column("metadata_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_size_bytes", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_type_id"],
            ["document_types.id"],
            name=op.f("fk_documents_document_type_id_document_types"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_documents_name_not_empty")),
        sa.CheckConstraint(
            "length(trim(original_filename)) > 0",
            name=op.f("ck_documents_original_filename_not_empty"),
        ),
        sa.CheckConstraint(
            "document_type_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
            name=op.f("ck_documents_document_type_id_snake_case"),
        ),
        sa.CheckConstraint("status in ('received')", name=op.f("ck_documents_status_supported")),
        sa.CheckConstraint(
            "length(trim(source)) > 0",
            name=op.f("ck_documents_source_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(connector)) > 0",
            name=op.f("ck_documents_connector_not_empty"),
        ),
        sa.CheckConstraint(
            "connector_correlation_id is null or length(trim(connector_correlation_id)) > 0",
            name=op.f("ck_documents_connector_correlation_id_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(storage_locator)) > 0",
            name=op.f("ck_documents_storage_locator_not_empty"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metadata_values) = 'object'",
            name=op.f("ck_documents_metadata_values_object"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_documents_updated_at_not_before_created_at"),
        ),
        sa.CheckConstraint(
            "content_size_bytes is null or content_size_bytes >= 0",
            name=op.f("ck_documents_content_size_bytes_non_negative"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(op.f("ix_documents_document_type_id"), "documents", ["document_type_id"])
    op.create_index(op.f("ix_documents_status"), "documents", ["status"])
    op.create_index(op.f("ix_documents_connector"), "documents", ["connector"])
    op.create_index(
        op.f("ix_documents_connector_correlation_id"),
        "documents",
        ["connector_correlation_id"],
    )
    op.create_index(op.f("ix_documents_source"), "documents", ["source"])
