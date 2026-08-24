"""Add manual upload actor metadata.

Revision ID: 20260629_0023
Revises: 20260629_0022
Create Date: 2026-06-29 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260629_0023"
down_revision: str | None = "20260629_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPLOAD_ACTOR_DISPLAY_NAME_MAX_LENGTH = 320
UPLOAD_ACTOR_USER_ID_MAX_LENGTH = 200


def upgrade() -> None:
    """Store audit-safe actor metadata for browser manual uploads."""

    op.add_column(
        "documents",
        sa.Column(
            "uploaded_by_user_id",
            sa.String(length=UPLOAD_ACTOR_USER_ID_MAX_LENGTH),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "uploaded_by_display_name",
            sa.String(length=UPLOAD_ACTOR_DISPLAY_NAME_MAX_LENGTH),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        op.f("ck_documents_uploaded_by_user_id_not_empty"),
        "documents",
        "uploaded_by_user_id is null or length(trim(uploaded_by_user_id)) > 0",
    )
    op.create_check_constraint(
        op.f("ck_documents_uploaded_by_display_name_not_empty"),
        "documents",
        "uploaded_by_display_name is null or length(trim(uploaded_by_display_name)) > 0",
    )
    op.create_check_constraint(
        op.f("ck_documents_uploaded_by_complete"),
        "documents",
        "(uploaded_by_user_id is null and uploaded_by_display_name is null) "
        "or (uploaded_by_user_id is not null and uploaded_by_display_name is not null)",
    )


def downgrade() -> None:
    """Remove manual upload actor metadata."""

    op.drop_constraint(
        op.f("ck_documents_uploaded_by_complete"),
        "documents",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_documents_uploaded_by_display_name_not_empty"),
        "documents",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_documents_uploaded_by_user_id_not_empty"),
        "documents",
        type_="check",
    )
    op.drop_column("documents", "uploaded_by_display_name")
    op.drop_column("documents", "uploaded_by_user_id")
