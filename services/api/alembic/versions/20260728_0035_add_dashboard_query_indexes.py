"""Add indexes used by the operational dashboard.

Revision ID: 20260728_0035
Revises: 20260728_0034
Create Date: 2026-07-28 00:00:01.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260728_0035"
down_revision: str | Sequence[str] | None = "20260728_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add bounded-window and latest-run lookup indexes."""

    op.create_index("ix_documents_created_at", "documents", ["created_at"], unique=False)
    op.create_index(
        "ix_documents_status_updated_at",
        "documents",
        ["status", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_ocr_pipeline_runs_completed_at",
        "ocr_pipeline_runs",
        ["completed_at"],
        unique=False,
    )
    op.create_index(
        "ix_ocr_pipeline_runs_document_created_at",
        "ocr_pipeline_runs",
        ["document_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove dashboard-specific lookup indexes."""

    op.drop_index(
        "ix_ocr_pipeline_runs_document_created_at",
        table_name="ocr_pipeline_runs",
    )
    op.drop_index("ix_ocr_pipeline_runs_completed_at", table_name="ocr_pipeline_runs")
    op.drop_index("ix_documents_status_updated_at", table_name="documents")
    op.drop_index("ix_documents_created_at", table_name="documents")
