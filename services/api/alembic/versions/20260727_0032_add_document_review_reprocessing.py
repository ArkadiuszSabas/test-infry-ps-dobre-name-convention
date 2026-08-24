"""Track Review versions that await document-type reprocessing.

Revision ID: 20260727_0032
Revises: 20260721_0031
Create Date: 2026-07-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0032"
down_revision: str | Sequence[str] | None = "20260721_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_review_versions",
        sa.Column(
            "is_reprocessing",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("document_review_versions", "is_reprocessing", server_default=None)


def downgrade() -> None:
    op.drop_column("document_review_versions", "is_reprocessing")
