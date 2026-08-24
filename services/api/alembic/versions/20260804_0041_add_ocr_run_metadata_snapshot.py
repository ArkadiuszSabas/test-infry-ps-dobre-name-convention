"""Persist API-owned metadata snapshots for OCR pipeline runs.

Revision ID: 20260804_0041
Revises: 20260803_0040
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260804_0041"
down_revision: str | Sequence[str] | None = "20260803_0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ocr_pipeline_runs",
        sa.Column(
            "metadata_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.alter_column("ocr_pipeline_runs", "metadata_snapshot", server_default=None)
    op.create_check_constraint(
        "metadata_snapshot_array",
        "ocr_pipeline_runs",
        "jsonb_typeof(metadata_snapshot) = 'array'",
    )


def downgrade() -> None:
    op.drop_constraint("metadata_snapshot_array", "ocr_pipeline_runs", type_="check")
    op.drop_column("ocr_pipeline_runs", "metadata_snapshot")
