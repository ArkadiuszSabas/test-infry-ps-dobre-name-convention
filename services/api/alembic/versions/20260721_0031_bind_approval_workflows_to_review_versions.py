"""Bind each current approval run to its Review version.

Revision ID: 20260721_0031
Revises: 20260716_0030
Create Date: 2026-07-21 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0031"
down_revision: str | Sequence[str] | None = "20260716_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_approval_workflows",
        sa.Column("review_version", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        update document_approval_workflows workflow
        set review_version = review.current_version
        from document_reviews review
        where review.document_id = workflow.document_id
        """
    )
    op.alter_column("document_approval_workflows", "review_version", nullable=False)
    op.create_check_constraint(
        op.f("ck_document_approval_workflows_review_version_positive"),
        "document_approval_workflows",
        "review_version > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_document_approval_workflows_review_version_positive"),
        "document_approval_workflows",
        type_="check",
    )
    op.drop_column("document_approval_workflows", "review_version")
