"""Add durable OCR event-control fields to execution attempts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_0045"
down_revision: str | Sequence[str] | None = "20260820_0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ocr_pipeline_run_attempts",
        sa.Column("execution_deadline_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ocr_pipeline_run_attempts",
        sa.Column("last_event_sequence", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_run_attempts_last_event_sequence_non_negative"),
        "ocr_pipeline_run_attempts",
        "last_event_sequence >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_ocr_pipeline_run_attempts_last_event_sequence_non_negative"),
        "ocr_pipeline_run_attempts",
        type_="check",
    )
    op.drop_column("ocr_pipeline_run_attempts", "last_event_sequence")
    op.drop_column("ocr_pipeline_run_attempts", "execution_deadline_at")
