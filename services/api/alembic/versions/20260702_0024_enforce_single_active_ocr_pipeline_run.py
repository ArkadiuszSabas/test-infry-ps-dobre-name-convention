"""Enforce one active OCR pipeline run per document.

Revision ID: 20260702_0024
Revises: 20260701_0024
Create Date: 2026-07-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "20260702_0024"
down_revision: str | None = "20260701_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_RUN_INDEX_NAME = "uq_ocr_pipeline_runs_active_document_id"
ACTIVE_RUN_FILTER_SQL = "status in ('pending', 'running')"


def upgrade() -> None:
    """Reject parallel pending/running OCR runs for the same document."""

    _guard_no_duplicate_active_document_runs(op.get_bind())
    op.create_index(
        ACTIVE_RUN_INDEX_NAME,
        "ocr_pipeline_runs",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_RUN_FILTER_SQL),
    )


def downgrade() -> None:
    """Remove the active-run uniqueness guard."""

    op.drop_index(ACTIVE_RUN_INDEX_NAME, table_name="ocr_pipeline_runs")


def _guard_no_duplicate_active_document_runs(connection: Connection) -> None:
    """Block the guard migration when duplicate active runs already exist."""

    duplicate_document_count = int(
        connection.scalar(
            sa.text(
                """
                select count(*)
                from (
                    select document_id
                    from ocr_pipeline_runs
                    where status in ('pending', 'running')
                    group by document_id
                    having count(*) > 1
                ) duplicate_active_documents
                """,
            ),
        )
        or 0
    )
    if duplicate_document_count:
        raise RuntimeError(
            "Cannot enforce single active OCR pipeline run while duplicate active "
            "runs exist for documents: "
            f"duplicate_document_count={duplicate_document_count}."
        )
