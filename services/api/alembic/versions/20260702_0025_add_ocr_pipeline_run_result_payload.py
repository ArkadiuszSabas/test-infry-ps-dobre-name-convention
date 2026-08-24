"""Add OCR pipeline run result payload.

Revision ID: 20260702_0025
Revises: 20260702_0024
Create Date: 2026-07-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260702_0025"
down_revision: str | None = "20260702_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store safe OCR display payloads produced by completed runs."""

    op.add_column(
        "ocr_pipeline_runs",
        sa.Column(
            "result_payload",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_runs_result_payload_object"),
        "ocr_pipeline_runs",
        "result_payload is null or jsonb_typeof(result_payload) = 'object'",
    )


def downgrade() -> None:
    """Remove run result payload persistence after an empty-state guard."""

    _guard_safe_ocr_pipeline_run_result_payload_downgrade(op.get_bind())

    op.drop_constraint(
        op.f("ck_ocr_pipeline_runs_result_payload_object"),
        "ocr_pipeline_runs",
        type_="check",
    )
    op.drop_column("ocr_pipeline_runs", "result_payload")


def _guard_safe_ocr_pipeline_run_result_payload_downgrade(connection: Connection) -> None:
    """Block downgrade once OCR pipeline run result payloads exist."""

    row_count = int(
        connection.scalar(
            sa.text("select count(*) from ocr_pipeline_runs where result_payload is not null"),
        )
        or 0
    )
    if row_count:
        raise RuntimeError(
            "Cannot downgrade OCR pipeline run result payload persistence while payloads exist: "
            f"ocr_pipeline_runs.result_payload={row_count}."
        )
