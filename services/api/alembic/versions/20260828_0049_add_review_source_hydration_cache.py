"""Cache repaired pipeline source locations without creating Review versions.

Revision ID: 20260828_0049
Revises: 20260825_0048
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_0049"
down_revision: str | Sequence[str] | None = "20260825_0048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_review_versions",
        sa.Column(
            "pipeline_sources_hydrated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("document_review_versions", "pipeline_sources_hydrated")
