"""Add session authentication context.

Revision ID: 20260521_0003
Revises: 20260520_0002
Create Date: 2026-05-21 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260521_0003"
down_revision: str | None = "20260520_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the provider context stored with each browser session."""

    op.add_column(
        "user_sessions",
        sa.Column("auth_provider", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "user_sessions",
        sa.Column("identity_link_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute("update user_sessions set auth_provider = 'local' where auth_provider is null")
    op.alter_column("user_sessions", "auth_provider", nullable=False)
    op.create_check_constraint(
        op.f("ck_user_sessions_auth_provider_supported"),
        "user_sessions",
        "auth_provider in ('local', 'entra_id')",
    )
    op.create_check_constraint(
        op.f("ck_user_sessions_identity_link_matches_auth_provider"),
        "user_sessions",
        "(auth_provider = 'local' and identity_link_id is null) "
        "or (auth_provider = 'entra_id' and identity_link_id is not null)",
    )


def downgrade() -> None:
    """Remove the provider context stored with each browser session."""

    op.drop_constraint(
        op.f("ck_user_sessions_auth_provider_supported"),
        "user_sessions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_user_sessions_identity_link_matches_auth_provider"),
        "user_sessions",
        type_="check",
    )
    op.drop_column("user_sessions", "identity_link_id")
    op.drop_column("user_sessions", "auth_provider")
