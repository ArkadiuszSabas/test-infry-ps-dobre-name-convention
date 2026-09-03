"""Add durable serial OCR pipeline comparison metadata.

Revision ID: 20260825_0048
Revises: 20260822_0047
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260825_0048"
down_revision: str | Sequence[str] | None = "20260822_0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ocr_pipeline_runs",
        sa.Column("comparison_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ocr_pipeline_runs",
        sa.Column("comparison_role", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "ocr_pipeline_runs",
        sa.Column(
            "comparison_baseline_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_runs_comparison_identity_valid"),
        "ocr_pipeline_runs",
        "(comparison_id is null and comparison_role is null) or "
        "(comparison_id is not null and comparison_role in ('vision', 'baseline'))",
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_runs_comparison_baseline_snapshot_valid"),
        "ocr_pipeline_runs",
        "(comparison_role = 'vision' and comparison_baseline_snapshot is not null "
        "and jsonb_typeof(comparison_baseline_snapshot) = 'object') or "
        "(comparison_role is distinct from 'vision' and comparison_baseline_snapshot is null)",
    )
    op.create_index(
        "uq_ocr_pipeline_runs_comparison_role",
        "ocr_pipeline_runs",
        ["comparison_id", "comparison_role"],
        unique=True,
        postgresql_where=sa.text("comparison_id is not null"),
    )


def downgrade() -> None:
    connection = op.get_bind()
    comparison_count = int(
        connection.scalar(
            sa.text("select count(*) from ocr_pipeline_runs where comparison_id is not null")
        )
        or 0
    )
    if comparison_count:
        raise RuntimeError("Cannot downgrade while OCR pipeline comparison history exists.")
    op.drop_index("uq_ocr_pipeline_runs_comparison_role", table_name="ocr_pipeline_runs")
    op.drop_constraint(
        op.f("ck_ocr_pipeline_runs_comparison_baseline_snapshot_valid"),
        "ocr_pipeline_runs",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_ocr_pipeline_runs_comparison_identity_valid"),
        "ocr_pipeline_runs",
        type_="check",
    )
    op.drop_column("ocr_pipeline_runs", "comparison_baseline_snapshot")
    op.drop_column("ocr_pipeline_runs", "comparison_role")
    op.drop_column("ocr_pipeline_runs", "comparison_id")
