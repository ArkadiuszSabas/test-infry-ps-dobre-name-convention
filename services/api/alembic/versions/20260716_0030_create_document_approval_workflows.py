"""Create persistent four-eyes document approval workflow state.

Revision ID: 20260716_0030
Revises: 20260715_0029
Create Date: 2026-07-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260716_0030"
down_revision: str | Sequence[str] | None = "20260715_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_documents_status_supported"),
        "documents",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_documents_status_supported"),
        "documents",
        "status in ('received', 'waiting_for_review', 'in_review', 'approved')",
    )
    op.create_table(
        "document_approval_workflows",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_run", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "current_run > 0", name=op.f("ck_document_approval_workflows_run_positive")
        ),
        sa.CheckConstraint(
            "status in ('waiting_for_review', 'in_review', 'approved')",
            name=op.f("ck_document_approval_workflows_status_supported"),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("document_id", name=op.f("pk_document_approval_workflows")),
    )
    op.create_table(
        "document_approval_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.String(length=200), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "run_number > 0", name=op.f("ck_document_approval_decisions_run_positive")
        ),
        sa.CheckConstraint(
            "step_number in (1, 2)", name=op.f("ck_document_approval_decisions_step_supported")
        ),
        sa.CheckConstraint(
            "decision in ('approved', 'rejected')",
            name=op.f("ck_document_approval_decisions_decision_supported"),
        ),
        sa.CheckConstraint(
            "length(trim(actor_id)) > 0",
            name=op.f("ck_document_approval_decisions_actor_id_not_empty"),
        ),
        sa.CheckConstraint(
            "comment is null or length(trim(comment)) > 0",
            name=op.f("ck_document_approval_decisions_comment_not_empty"),
        ),
        sa.CheckConstraint(
            "decision <> 'rejected' or comment is not null",
            name=op.f("ck_document_approval_decisions_rejection_comment_required"),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_approval_decisions")),
    )
    op.execute(
        """
        insert into document_approval_workflows (document_id, current_run, status, updated_at)
        select document_id, 1, 'waiting_for_review', current_timestamp
        from document_reviews
        """
    )
    op.execute(
        """
        update documents
        set status = 'waiting_for_review', updated_at = current_timestamp
        where status = 'received'
          and id in (select document_id from document_reviews)
        """
    )
    op.create_index(
        "uq_document_approval_decisions_document_run_step",
        "document_approval_decisions",
        ["document_id", "run_number", "step_number"],
        unique=True,
    )


def downgrade() -> None:
    _guard_safe_approval_workflow_downgrade(op.get_bind())
    op.drop_index(
        "uq_document_approval_decisions_document_run_step",
        table_name="document_approval_decisions",
    )
    op.drop_table("document_approval_decisions")
    op.drop_table("document_approval_workflows")
    op.drop_constraint(
        op.f("ck_documents_status_supported"),
        "documents",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_documents_status_supported"),
        "documents",
        "status in ('received')",
    )


def _guard_safe_approval_workflow_downgrade(connection: Connection) -> None:
    """Block destructive rollback after immutable approval history exists."""

    decision_count = int(
        connection.scalar(sa.text("select count(*) from document_approval_decisions")) or 0
    )
    if decision_count:
        raise RuntimeError(
            "Cannot downgrade document approval workflows while decision history exists: "
            f"document_approval_decisions={decision_count}."
        )
