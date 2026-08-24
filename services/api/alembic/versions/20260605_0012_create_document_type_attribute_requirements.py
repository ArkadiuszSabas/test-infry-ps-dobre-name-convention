"""Create document type attribute requirements table.

Revision ID: 20260605_0012
Revises: 20260602_0011
Create Date: 2026-06-05 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260605_0012"
down_revision: str | None = "20260602_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the API-owned document type attribute requirement table."""

    op.create_table(
        "attribute_requirements",
        sa.Column("document_type_id", sa.String(length=80), nullable=False),
        sa.Column("attribute_id", sa.String(length=80), nullable=False),
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
            "("
            "required = true "
            "and missing_required_action in ('block_approval', 'require_review')"
            ") or (required = false and missing_required_action is null)",
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
        unique=False,
    )


def downgrade() -> None:
    """Drop the API-owned document type attribute requirement table."""

    op.drop_index(
        op.f("ix_attribute_requirements_attribute_id"),
        table_name="attribute_requirements",
    )
    op.drop_table("attribute_requirements")
