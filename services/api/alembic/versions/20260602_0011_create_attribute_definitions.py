"""Create attribute definitions table.

Revision ID: 20260602_0011
Revises: 20260529_0010
Create Date: 2026-06-02 10:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260602_0011"
down_revision: str | None = "20260529_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
ALLOWED_VALUE_MAX_LENGTH = 200
COMMENT_MAX_LENGTH = 2000


def upgrade() -> None:
    """Create the API-owned attribute definition catalog table."""

    op.execute(
        """
        create function jsonb_text_array_is_valid(value jsonb, max_length integer)
        returns boolean
        language sql
        immutable
        strict
        as $$
            select jsonb_typeof(value) = 'array'
               and not exists (
                   select 1
                   from jsonb_array_elements(value) as element(item)
                   where jsonb_typeof(element.item) <> 'string'
                      or length(trim(both from element.item #>> '{}')) = 0
                      or length(element.item #>> '{}') > max_length
               )
        $$;
        """,
    )
    op.create_table(
        "attribute_definitions",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("allowed_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.String(length=COMMENT_MAX_LENGTH), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attribute_definitions")),
    )
    op.create_index(
        op.f("ix_attribute_definitions_category"),
        "attribute_definitions",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attribute_definitions_status"),
        "attribute_definitions",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the API-owned attribute definition catalog table."""

    op.drop_index(op.f("ix_attribute_definitions_status"), table_name="attribute_definitions")
    op.drop_index(op.f("ix_attribute_definitions_category"), table_name="attribute_definitions")
    op.drop_table("attribute_definitions")
    op.execute("drop function jsonb_text_array_is_valid(jsonb, integer)")
