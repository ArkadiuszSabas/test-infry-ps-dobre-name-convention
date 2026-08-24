"""Add document content size.

Revision ID: 20260616_0016
Revises: 20260611_0015
Create Date: 2026-06-16 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_0016"
down_revision: str | None = "20260611_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Track stored document content size and source lookup."""

    op.add_column(
        "documents",
        sa.Column(
            "content_size_bytes",
            sa.BigInteger(),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        op.f("ck_documents_content_size_bytes_non_negative"),
        "documents",
        "content_size_bytes is null or content_size_bytes >= 0",
    )
    op.create_index(op.f("ix_documents_source"), "documents", ["source"], unique=False)


def downgrade() -> None:
    """Remove stored document content size and source lookup."""

    op.drop_index(op.f("ix_documents_source"), table_name="documents")
    op.drop_constraint(
        op.f("ck_documents_content_size_bytes_non_negative"),
        "documents",
        type_="check",
    )
    op.drop_column("documents", "content_size_bytes")
