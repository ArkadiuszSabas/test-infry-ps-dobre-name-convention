"""Add the API-owned OCR run request outbox.

Revision ID: 20260820_0044
Revises: 20260818_0043
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260820_0044"
down_revision: str | Sequence[str] | None = "20260818_0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ocr_pipeline_run_outbox",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("topic", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publish_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "length(trim(topic)) > 0", name=op.f("ck_ocr_run_outbox_topic_not_empty")
        ),
        sa.CheckConstraint(
            "length(trim(event_type)) > 0", name=op.f("ck_ocr_run_outbox_event_type_not_empty")
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'", name=op.f("ck_ocr_run_outbox_payload_object")
        ),
        sa.CheckConstraint(
            "publish_attempts >= 0", name=op.f("ck_ocr_run_outbox_attempts_non_negative")
        ),
        sa.ForeignKeyConstraint(["run_id"], ["ocr_pipeline_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ocr_pipeline_run_outbox")),
    )
    op.create_index("ix_ocr_pipeline_run_outbox_run_id", "ocr_pipeline_run_outbox", ["run_id"])
    op.create_index(
        "ix_ocr_pipeline_run_outbox_pending",
        "ocr_pipeline_run_outbox",
        ["created_at"],
        postgresql_where=sa.text("published_at is null"),
    )


def downgrade() -> None:
    op.drop_index("ix_ocr_pipeline_run_outbox_pending", table_name="ocr_pipeline_run_outbox")
    op.drop_index("ix_ocr_pipeline_run_outbox_run_id", table_name="ocr_pipeline_run_outbox")
    op.drop_table("ocr_pipeline_run_outbox")
