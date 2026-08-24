"""Allow soft-deleted users.

Revision ID: 20260624_0020
Revises: 20260624_0019
Create Date: 2026-06-24 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "20260624_0020"
down_revision: str | None = "20260624_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow the API to soft-delete users while keeping audit-linked rows."""

    op.drop_constraint(
        op.f("ck_users_status_supported"),
        "users",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_users_status_supported"),
        "users",
        "status in ('active', 'inactive', 'deleted')",
    )


def downgrade() -> None:
    """Restore the previous active/inactive user status constraint."""

    _guard_no_deleted_users(op.get_bind())

    op.drop_constraint(
        op.f("ck_users_status_supported"),
        "users",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_users_status_supported"),
        "users",
        "status in ('active', 'inactive')",
    )


def _guard_no_deleted_users(connection: Connection) -> None:
    """Fail before restoring a constraint that would reject deleted users."""

    deleted_user_exists = connection.scalar(
        sa.text("select exists(select 1 from users where status = 'deleted')"),
    )
    if deleted_user_exists:
        raise RuntimeError(
            "Cannot downgrade user status constraint while deleted users exist.",
        )
