"""Add durable OCR admission and delayed redispatch.

Revision ID: 20260822_0046
Revises: 20260820_0045
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0046"
down_revision: str | Sequence[str] | None = "20260820_0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ocr_pipeline_run_outbox",
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "ocr_pipeline_run_outbox",
        sa.Column("dedupe_key", sa.String(length=160), nullable=True),
    )
    op.drop_index("ix_ocr_pipeline_run_outbox_pending", table_name="ocr_pipeline_run_outbox")
    op.create_index(
        "ix_ocr_pipeline_run_outbox_available",
        "ocr_pipeline_run_outbox",
        ["available_at", "created_at"],
        postgresql_where=sa.text("published_at is null"),
    )
    op.create_index(
        "uq_ocr_pipeline_run_outbox_pending_dedupe_key",
        "ocr_pipeline_run_outbox",
        ["dedupe_key"],
        unique=True,
        postgresql_where=sa.text("published_at is null and dedupe_key is not null"),
    )

    op.create_table(
        "ocr_pipeline_run_capacity_lock",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.CheckConstraint("id = 1", name=op.f("ck_ocr_pipeline_run_capacity_lock_singleton")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ocr_pipeline_run_capacity_lock")),
    )
    op.execute("insert into ocr_pipeline_run_capacity_lock (id) values (1)")

    op.drop_index(
        "uq_ocr_pipeline_run_attempts_active_run_id",
        table_name="ocr_pipeline_run_attempts",
    )
    op.drop_constraint(
        op.f("ck_ocr_pipeline_run_attempts_status_supported"),
        "ocr_pipeline_run_attempts",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_ocr_pipeline_run_attempts_completion_matches_status"),
        "ocr_pipeline_run_attempts",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_run_attempts_status_supported"),
        "ocr_pipeline_run_attempts",
        "status in ('reserved', 'running', 'succeeded', 'partial_failed', "
        "'failed', 'indeterminate', 'lost')",
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_run_attempts_completion_matches_status"),
        "ocr_pipeline_run_attempts",
        "(status in ('reserved', 'running') and completed_at is null) or "
        "(status not in ('reserved', 'running') and completed_at is not null)",
    )
    op.create_index(
        "uq_ocr_pipeline_run_attempts_active_run_id",
        "ocr_pipeline_run_attempts",
        ["run_id"],
        unique=True,
        postgresql_where=sa.text("status in ('reserved', 'running')"),
    )


def downgrade() -> None:
    op.execute("update ocr_pipeline_run_attempts set status = 'running' where status = 'reserved'")
    op.drop_index(
        "uq_ocr_pipeline_run_attempts_active_run_id",
        table_name="ocr_pipeline_run_attempts",
    )
    op.drop_constraint(
        op.f("ck_ocr_pipeline_run_attempts_completion_matches_status"),
        "ocr_pipeline_run_attempts",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_ocr_pipeline_run_attempts_status_supported"),
        "ocr_pipeline_run_attempts",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_run_attempts_status_supported"),
        "ocr_pipeline_run_attempts",
        "status in ('running', 'succeeded', 'partial_failed', 'failed', 'indeterminate', 'lost')",
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_run_attempts_completion_matches_status"),
        "ocr_pipeline_run_attempts",
        "(status = 'running' and completed_at is null) or "
        "(status <> 'running' and completed_at is not null)",
    )
    op.create_index(
        "uq_ocr_pipeline_run_attempts_active_run_id",
        "ocr_pipeline_run_attempts",
        ["run_id"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
    )
    op.drop_table("ocr_pipeline_run_capacity_lock")
    op.drop_index(
        "uq_ocr_pipeline_run_outbox_pending_dedupe_key",
        table_name="ocr_pipeline_run_outbox",
    )
    op.drop_index("ix_ocr_pipeline_run_outbox_available", table_name="ocr_pipeline_run_outbox")
    op.create_index(
        "ix_ocr_pipeline_run_outbox_pending",
        "ocr_pipeline_run_outbox",
        ["created_at"],
        postgresql_where=sa.text("published_at is null"),
    )
    op.drop_column("ocr_pipeline_run_outbox", "dedupe_key")
    op.drop_column("ocr_pipeline_run_outbox", "available_at")
