"""Extend browser session diagnostics.

Revision ID: 20260527_0007
Revises: 20260525_0006
Create Date: 2026-05-27 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260527_0007"
down_revision: str | None = "20260525_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add privacy-aware metadata and revocation reason fields."""

    op.add_column(
        "user_sessions",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_sessions",
        sa.Column("revoked_reason", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "user_sessions",
        sa.Column("client_label", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "user_sessions",
        sa.Column("client_fingerprint", sa.String(length=80), nullable=True),
    )
    op.execute("update user_sessions set last_seen_at = created_at where last_seen_at is null")
    op.execute(
        "update user_sessions set revoked_reason = 'unknown' "
        "where revoked_at is not null and revoked_reason is null",
    )
    op.alter_column("user_sessions", "last_seen_at", nullable=False)
    op.create_check_constraint(
        op.f("ck_user_sessions_last_seen_at_not_before_created_at"),
        "user_sessions",
        "created_at <= last_seen_at",
    )
    op.create_check_constraint(
        op.f("ck_user_sessions_revoked_reason_supported"),
        "user_sessions",
        "revoked_reason is null or revoked_reason in ("
        "'user_logout', 'user_revoked', 'admin_revoked', "
        "'account_disabled', 'password_reset', 'unknown')",
    )
    op.create_check_constraint(
        op.f("ck_user_sessions_revoked_reason_matches_revoked_at"),
        "user_sessions",
        "(revoked_at is null and revoked_reason is null) "
        "or (revoked_at is not null and revoked_reason is not null)",
    )
    op.create_check_constraint(
        op.f("ck_user_sessions_client_label_not_empty"),
        "user_sessions",
        "client_label is null or length(trim(client_label)) > 0",
    )
    op.create_check_constraint(
        op.f("ck_user_sessions_client_fingerprint_not_empty"),
        "user_sessions",
        "client_fingerprint is null or length(trim(client_fingerprint)) > 0",
    )


def downgrade() -> None:
    """Remove extended browser session diagnostics."""

    op.drop_constraint(
        op.f("ck_user_sessions_client_fingerprint_not_empty"),
        "user_sessions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_user_sessions_client_label_not_empty"),
        "user_sessions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_user_sessions_revoked_reason_matches_revoked_at"),
        "user_sessions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_user_sessions_revoked_reason_supported"),
        "user_sessions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_user_sessions_last_seen_at_not_before_created_at"),
        "user_sessions",
        type_="check",
    )
    op.drop_column("user_sessions", "client_fingerprint")
    op.drop_column("user_sessions", "client_label")
    op.drop_column("user_sessions", "revoked_reason")
    op.drop_column("user_sessions", "last_seen_at")
