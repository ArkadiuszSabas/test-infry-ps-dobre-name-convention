"""Apply saved approval settings to workflows without decision history.

Revision ID: 20260731_0039
Revises: 20260731_0038
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0039"
down_revision: str | Sequence[str] | None = "20260731_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            select documents.id
            from documents
            join document_approval_workflows
              on document_approval_workflows.document_id = documents.id
            where document_approval_workflows.status = 'waiting_for_review'
              and not exists (
                select 1
                from document_approval_decisions
                where document_approval_decisions.document_id = documents.id
              )
            order by documents.id
            for update of documents
            """
        )
    ).all()
    connection.execute(
        sa.text(
            """
            update document_approval_workflows as workflow
            set required_approvals = settings.required_approvals,
                updated_at = greatest(workflow.updated_at, settings.updated_at)
            from document_approval_settings as settings
            where settings.settings_key = 'default'
              and workflow.status = 'waiting_for_review'
              and workflow.required_approvals <> settings.required_approvals
              and not exists (
                select 1
                from document_approval_decisions as decision
                where decision.document_id = workflow.document_id
              )
            """
        )
    )


def downgrade() -> None:
    # The prior per-workflow value cannot be reconstructed after synchronization.
    # Keeping the current business configuration is safer than inventing a rollback value.
    pass
