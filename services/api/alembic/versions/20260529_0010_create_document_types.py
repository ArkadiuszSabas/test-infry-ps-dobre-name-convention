"""Create document types table.

Revision ID: 20260529_0010
Revises: 20260528_0009
Create Date: 2026-05-29 00:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0010"
down_revision: str | None = "20260528_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
DESCRIPTION_MAX_LENGTH = 2000


def upgrade() -> None:
    """Create the API-owned document type catalog table."""

    op.create_table(
        "document_types",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "description",
            sa.String(length=DESCRIPTION_MAX_LENGTH),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
            name=op.f("ck_document_types_id_snake_case"),
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name=op.f("ck_document_types_name_not_empty"),
        ),
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
    op.create_index(
        op.f("ix_document_types_status"),
        "document_types",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the API-owned document type catalog table."""

    op.drop_index(op.f("ix_document_types_status"), table_name="document_types")
    op.drop_table("document_types")
