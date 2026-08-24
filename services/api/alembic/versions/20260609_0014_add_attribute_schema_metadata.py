"""Add attribute schema metadata.

Revision ID: 20260609_0014
Revises: 20260608_0013
Create Date: 2026-06-09 09:00:00.000000
"""

from collections.abc import Sequence
from typing import cast

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260609_0014"
down_revision: str | None = "20260608_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Extend attribute definitions with typed metadata schema fields."""

    op.add_column(
        "attribute_definitions",
        sa.Column(
            "data_type",
            sa.String(length=32),
            nullable=False,
            server_default="legacy_scalar",
        ),
    )
    op.add_column(
        "attribute_definitions",
        sa.Column(
            "constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "attribute_definitions",
        sa.Column(
            "schema_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.alter_column("attribute_definitions", "data_type", server_default=None)
    op.alter_column("attribute_definitions", "constraints", server_default=None)
    op.alter_column("attribute_definitions", "schema_version", server_default=None)
    op.create_check_constraint(
        op.f("ck_attribute_definitions_data_type_supported"),
        "attribute_definitions",
        "data_type in ("
        "'legacy_scalar', 'string', 'integer', 'number', 'boolean', 'date', 'datetime'"
        ")",
    )
    op.create_check_constraint(
        op.f("ck_attribute_definitions_constraints_object"),
        "attribute_definitions",
        "jsonb_typeof(constraints) = 'object'",
    )
    op.create_check_constraint(
        op.f("ck_attribute_definitions_allowed_values_match_data_type"),
        "attribute_definitions",
        "data_type in ('legacy_scalar', 'string') or jsonb_array_length(allowed_values) = 0",
    )
    op.create_check_constraint(
        op.f("ck_attribute_definitions_schema_version_positive"),
        "attribute_definitions",
        "schema_version > 0",
    )


def downgrade() -> None:
    """Remove typed metadata schema fields from attribute definitions."""

    _guard_safe_downgrade_attribute_schema_metadata(op.get_bind())
    op.drop_constraint(
        op.f("ck_attribute_definitions_schema_version_positive"),
        "attribute_definitions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_attribute_definitions_allowed_values_match_data_type"),
        "attribute_definitions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_attribute_definitions_constraints_object"),
        "attribute_definitions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_attribute_definitions_data_type_supported"),
        "attribute_definitions",
        type_="check",
    )
    op.drop_column("attribute_definitions", "schema_version")
    op.drop_column("attribute_definitions", "constraints")
    op.drop_column("attribute_definitions", "data_type")


def _guard_safe_downgrade_attribute_schema_metadata(connection: Connection) -> None:
    """Block downgrade after typed attribute schema metadata has been configured."""

    typed_schema_rows = cast(
        int,
        connection.scalar(
            sa.text(
                """
                select count(*)
                from attribute_definitions
                where data_type <> 'legacy_scalar'
                   or constraints <> '{}'::jsonb
                   or schema_version <> 1
                """,
            ),
        ),
    )
    if typed_schema_rows:
        raise RuntimeError(
            "Cannot downgrade attribute schema metadata after typed attribute schema data "
            "has been configured.",
        )
