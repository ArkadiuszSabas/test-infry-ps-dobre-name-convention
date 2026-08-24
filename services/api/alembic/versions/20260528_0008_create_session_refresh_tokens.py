"""Create session refresh tokens table.

Revision ID: 20260528_0008
Revises: 20260527_0007
Create Date: 2026-05-26 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260528_0008"
down_revision: str | None = "20260527_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create rotating refresh token persistence."""

    op.create_table(
        "session_refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reused_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "created_at < expires_at",
            name=op.f("ck_session_refresh_tokens_expires_at_after_created_at"),
        ),
        sa.CheckConstraint(
            "rotated_at is null or rotated_at >= created_at",
            name=op.f("ck_session_refresh_tokens_rotated_at_not_before_created_at"),
        ),
        sa.CheckConstraint(
            "revoked_at is null or revoked_at >= created_at",
            name=op.f("ck_session_refresh_tokens_revoked_at_not_before_created_at"),
        ),
        sa.CheckConstraint(
            "reused_at is null or reused_at >= created_at",
            name=op.f("ck_session_refresh_tokens_reused_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["user_sessions.id"],
            name=op.f("fk_session_refresh_tokens_session_id_user_sessions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_refresh_tokens")),
        sa.UniqueConstraint(
            "token_hash",
            name=op.f("uq_session_refresh_tokens_token_hash"),
        ),
    )
    op.create_index(
        op.f("ix_session_refresh_tokens_family_id"),
        "session_refresh_tokens",
        ["family_id"],
    )


def downgrade() -> None:
    """Drop rotating refresh token persistence."""

    op.drop_index(
        op.f("ix_session_refresh_tokens_family_id"),
        table_name="session_refresh_tokens",
    )
    op.drop_table("session_refresh_tokens")
