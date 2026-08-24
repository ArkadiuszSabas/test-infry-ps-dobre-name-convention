"""Create documents table.

Revision ID: 20260608_0013
Revises: 20260605_0012
Create Date: 2026-06-08 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260608_0013"
down_revision: str | None = "20260605_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the API-owned document registry table."""

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("document_type_id", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("connector", sa.String(length=120), nullable=False),
        sa.Column("connector_correlation_id", sa.String(length=200), nullable=True),
        sa.Column("storage_locator", sa.String(length=2048), nullable=False),
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
            "length(trim(original_filename)) > 0",
            name=op.f("ck_documents_original_filename_not_empty"),
        ),
        sa.CheckConstraint(
            "document_type_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
            name=op.f("ck_documents_document_type_id_snake_case"),
        ),
        sa.CheckConstraint(
            "status in ('received')",
            name=op.f("ck_documents_status_supported"),
        ),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(
        op.f("ix_documents_document_type_id"),
        "documents",
        ["document_type_id"],
        unique=False,
    )
    op.create_index(op.f("ix_documents_status"), "documents", ["status"], unique=False)
    op.create_index(op.f("ix_documents_connector"), "documents", ["connector"], unique=False)
    op.create_index(
        op.f("ix_documents_connector_correlation_id"),
        "documents",
        ["connector_correlation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the API-owned document registry table."""

    op.drop_index(op.f("ix_documents_connector_correlation_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_connector"), table_name="documents")
    op.drop_index(op.f("ix_documents_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_document_type_id"), table_name="documents")
    op.drop_table("documents")
