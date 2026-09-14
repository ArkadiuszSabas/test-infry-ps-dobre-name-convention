"""Restrict runtime writes to initial workspace registry records.

Revision ID: 20260910_0052
Revises: 20260909_0051
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260910_0052"
down_revision: str | Sequence[str] | None = "20260909_0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Give API-created records immutable lifecycle defaults."""

    op.alter_column(
        "workspaces",
        "lifecycle",
        existing_type=sa.String(length=32),
        server_default=sa.text("'registered'"),
    )
    op.alter_column(
        "workspaces",
        "schema_state",
        existing_type=sa.String(length=32),
        server_default=sa.text("'pending'"),
    )
    op.alter_column(
        "workspace_provisioning_requests",
        "status",
        existing_type=sa.String(length=32),
        server_default=sa.text("'pending'"),
    )


def downgrade() -> None:
    """Remove only the default values; registry state remains intact."""

    op.alter_column(
        "workspace_provisioning_requests",
        "status",
        existing_type=sa.String(length=32),
        server_default=None,
    )
    op.alter_column(
        "workspaces",
        "schema_state",
        existing_type=sa.String(length=32),
        server_default=None,
    )
    op.alter_column(
        "workspaces",
        "lifecycle",
        existing_type=sa.String(length=32),
        server_default=None,
    )
