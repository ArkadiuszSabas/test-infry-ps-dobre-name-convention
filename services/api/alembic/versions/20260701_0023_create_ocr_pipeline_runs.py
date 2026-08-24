"""Create OCR pipeline run persistence.

Revision ID: 20260701_0023
Revises: 20260629_0023
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260701_0023"
down_revision: str | None = "20260629_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOCUMENT_REFERENCE_MAX_LENGTH = 256
CATALOG_VALUE_MAX_LENGTH = 256
ACTOR_ID_MAX_LENGTH = 128


def upgrade() -> None:
    """Create OCR pipeline run records."""

    op.create_table(
        "ocr_pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_version", sa.Integer(), nullable=False),
        sa.Column(
            "document_reference",
            sa.String(length=DOCUMENT_REFERENCE_MAX_LENGTH),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("compiled_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("catalog_version", sa.String(length=CATALOG_VALUE_MAX_LENGTH), nullable=True),
        sa.Column("catalog_hash", sa.String(length=CATALOG_VALUE_MAX_LENGTH), nullable=True),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("diagnostics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "error",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_by_actor_id", sa.String(length=ACTOR_ID_MAX_LENGTH), nullable=True),
        sa.CheckConstraint(
            "pipeline_version > 0",
            name=op.f("ck_ocr_pipeline_runs_pipeline_version_positive"),
        ),
        sa.CheckConstraint(
            "length(trim(document_reference)) > 0",
            name=op.f("ck_ocr_pipeline_runs_document_reference_not_empty"),
        ),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'succeeded', 'partial_failed', 'failed')",
            name=op.f("ck_ocr_pipeline_runs_status_supported"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(compiled_snapshot) = 'object'",
            name=op.f("ck_ocr_pipeline_runs_compiled_snapshot_object"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(steps) = 'array'",
            name=op.f("ck_ocr_pipeline_runs_steps_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metrics) = 'object'",
            name=op.f("ck_ocr_pipeline_runs_metrics_object"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(diagnostics) = 'array'",
            name=op.f("ck_ocr_pipeline_runs_diagnostics_array"),
        ),
        sa.CheckConstraint(
            "error is null or jsonb_typeof(error) = 'object'",
            name=op.f("ck_ocr_pipeline_runs_error_object"),
        ),
        sa.CheckConstraint(
            "catalog_version is null or length(trim(catalog_version)) > 0",
            name=op.f("ck_ocr_pipeline_runs_catalog_version_not_empty"),
        ),
        sa.CheckConstraint(
            "catalog_hash is null or length(trim(catalog_hash)) > 0",
            name=op.f("ck_ocr_pipeline_runs_catalog_hash_not_empty"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_ocr_pipeline_runs_updated_at_not_before_created_at"),
        ),
        sa.CheckConstraint(
            "started_at is null or created_at <= started_at",
            name=op.f("ck_ocr_pipeline_runs_started_at_not_before_created_at"),
        ),
        sa.CheckConstraint(
            "completed_at is null or started_at is not null",
            name=op.f("ck_ocr_pipeline_runs_completed_requires_started_at"),
        ),
        sa.CheckConstraint(
            "completed_at is null or started_at <= completed_at",
            name=op.f("ck_ocr_pipeline_runs_completed_at_not_before_started_at"),
        ),
        sa.CheckConstraint(
            "started_by_actor_id is null or length(trim(started_by_actor_id)) > 0",
            name=op.f("ck_ocr_pipeline_runs_started_by_actor_id_not_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_ocr_pipeline_runs_document_id_documents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_id"],
            ["ocr_pipeline_definitions.id"],
            name=op.f("fk_ocr_pipeline_runs_pipeline_id_ocr_pipeline_definitions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_id", "pipeline_version"],
            [
                "ocr_pipeline_definition_versions.definition_id",
                "ocr_pipeline_definition_versions.version_number",
            ],
            name=op.f("fk_ocr_pipeline_runs_pipeline_version"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ocr_pipeline_runs")),
    )
    op.create_index("ix_ocr_pipeline_runs_document_id", "ocr_pipeline_runs", ["document_id"])
    op.create_index("ix_ocr_pipeline_runs_pipeline_id", "ocr_pipeline_runs", ["pipeline_id"])
    op.create_index("ix_ocr_pipeline_runs_status", "ocr_pipeline_runs", ["status"])
    op.create_index("ix_ocr_pipeline_runs_created_at", "ocr_pipeline_runs", ["created_at"])


def downgrade() -> None:
    """Remove OCR pipeline run persistence after an empty-state guard."""

    _guard_safe_ocr_pipeline_run_downgrade(op.get_bind())

    op.drop_index("ix_ocr_pipeline_runs_created_at", table_name="ocr_pipeline_runs")
    op.drop_index("ix_ocr_pipeline_runs_status", table_name="ocr_pipeline_runs")
    op.drop_index("ix_ocr_pipeline_runs_pipeline_id", table_name="ocr_pipeline_runs")
    op.drop_index("ix_ocr_pipeline_runs_document_id", table_name="ocr_pipeline_runs")
    op.drop_table("ocr_pipeline_runs")


def _guard_safe_ocr_pipeline_run_downgrade(connection: Connection) -> None:
    """Block downgrade once OCR pipeline run state exists."""

    row_count = int(connection.scalar(sa.text("select count(*) from ocr_pipeline_runs")) or 0)
    if row_count:
        raise RuntimeError(
            "Cannot downgrade OCR pipeline run persistence while run state exists: "
            f"ocr_pipeline_runs={row_count}.",
        )
