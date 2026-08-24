"""Create local login attempts table.

Revision ID: 20260525_0006
Revises: 20260521_0005
Create Date: 2026-05-25 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260525_0006"
down_revision: str | None = "20260521_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create local login brute-force hardening state."""

    op.create_table(
        "local_login_attempts",
        sa.Column("login", sa.String(length=320), nullable=False),
        sa.Column("failed_attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_failed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "length(trim(login)) > 0",
            name=op.f("ck_local_login_attempts_login_not_empty"),
        ),
        sa.CheckConstraint(
            "failed_attempt_count >= 1",
            name=op.f("ck_local_login_attempts_failed_attempt_count_positive"),
        ),
        sa.CheckConstraint(
            "locked_until is null or locked_until >= last_failed_at",
            name=op.f("ck_local_login_attempts_locked_until_not_before_last_failed_at"),
        ),
        sa.PrimaryKeyConstraint("login", name=op.f("pk_local_login_attempts")),
    )


def downgrade() -> None:
    """Drop local login brute-force hardening state."""

    op.drop_table("local_login_attempts")
