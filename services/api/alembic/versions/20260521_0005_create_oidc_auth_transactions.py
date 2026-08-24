"""Create OIDC auth transactions table.

Revision ID: 20260521_0005
Revises: 20260521_0004
Create Date: 2026-05-21 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260521_0005"
down_revision: str | None = "20260521_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create short-lived server-side OIDC login transaction storage."""

    op.create_table(
        "oidc_auth_transactions",
        sa.Column("state_hash", sa.String(length=128), nullable=False),
        sa.Column("nonce_hash", sa.String(length=128), nullable=False),
        sa.Column("browser_binding_hash", sa.String(length=128), nullable=False),
        sa.Column("pkce_verifier", sa.String(length=128), nullable=False),
        sa.Column("redirect_uri", sa.String(length=2048), nullable=False),
        sa.Column("redirect_target", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "length(trim(state_hash)) > 0",
            name=op.f("ck_oidc_auth_transactions_state_hash_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(nonce_hash)) > 0",
            name=op.f("ck_oidc_auth_transactions_nonce_hash_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(browser_binding_hash)) > 0",
            name=op.f("ck_oidc_auth_transactions_browser_binding_hash_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(pkce_verifier)) > 0",
            name=op.f("ck_oidc_auth_transactions_pkce_verifier_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(redirect_uri)) > 0",
            name=op.f("ck_oidc_auth_transactions_redirect_uri_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(redirect_target)) > 0",
            name=op.f("ck_oidc_auth_transactions_redirect_target_not_empty"),
        ),
        sa.CheckConstraint(
            "created_at < expires_at",
            name=op.f("ck_oidc_auth_transactions_expires_at_after_created_at"),
        ),
        sa.CheckConstraint(
            "used_at is null or used_at >= created_at",
            name=op.f("ck_oidc_auth_transactions_used_at_not_before_created_at"),
        ),
        sa.PrimaryKeyConstraint(
            "state_hash",
            name=op.f("pk_oidc_auth_transactions"),
        ),
    )


def downgrade() -> None:
    """Drop OIDC login transaction storage."""

    op.drop_table("oidc_auth_transactions")
