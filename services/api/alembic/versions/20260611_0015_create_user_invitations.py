"""Create user invitations.

Revision ID: 20260611_0015
Revises: 20260609_0014
Create Date: 2026-06-11 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260611_0015"
down_revision: str | None = "20260609_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create admin-owned user invitation lifecycle table."""

    op.create_table(
        "user_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("roles", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "length(trim(email)) > 0",
            name=op.f("ck_user_invitations_email_not_empty"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(roles) = 'array' and jsonb_array_length(roles) > 0",
            name=op.f("ck_user_invitations_roles_non_empty_array"),
        ),
        sa.CheckConstraint(
            "status in ('pending', 'cancelled', 'accepted')",
            name=op.f("ck_user_invitations_status_supported"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_user_invitations_updated_at_not_before_created_at"),
        ),
        sa.CheckConstraint(
            "created_at < expires_at",
            name=op.f("ck_user_invitations_expires_at_after_created_at"),
        ),
        sa.CheckConstraint(
            "(status = 'cancelled' and cancelled_at is not null "
            "and cancelled_by_user_id is not null) "
            "or (status <> 'cancelled' and cancelled_at is null "
            "and cancelled_by_user_id is null)",
            name=op.f("ck_user_invitations_cancellation_metadata_matches_status"),
        ),
        sa.CheckConstraint(
            "(status = 'accepted' and accepted_at is not null "
            "and accepted_by_user_id is not null) "
            "or (status <> 'accepted' and accepted_at is null "
            "and accepted_by_user_id is null)",
            name=op.f("ck_user_invitations_acceptance_metadata_matches_status"),
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by_user_id"],
            ["users.id"],
            name=op.f("fk_user_invitations_accepted_by_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by_user_id"],
            ["users.id"],
            name=op.f("fk_user_invitations_cancelled_by_user_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_user_invitations_created_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_invitations")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_user_invitations_token_hash")),
    )
    op.create_index(
        "ix_user_invitations_email",
        "user_invitations",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_user_invitations_status",
        "user_invitations",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove admin-owned user invitation lifecycle table."""

    op.drop_index("ix_user_invitations_status", table_name="user_invitations")
    op.drop_index("ix_user_invitations_email", table_name="user_invitations")
    op.drop_table("user_invitations")
