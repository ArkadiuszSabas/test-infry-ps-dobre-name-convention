"""Configure the number of reviewers for new document approval workflows.

Revision ID: 20260731_0038
Revises: 20260728_0037
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0038"
down_revision: str | Sequence[str] | None = "20260728_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_approval_workflows",
        sa.Column(
            "required_approvals",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("2"),
        ),
    )
    op.create_check_constraint(
        op.f("ck_document_approval_workflows_required_approvals_supported"),
        "document_approval_workflows",
        "required_approvals in (1, 2)",
    )
    op.create_table(
        "document_approval_settings",
        sa.Column("settings_key", sa.String(length=50), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("required_approvals", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by_actor_id", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "settings_key = 'default'",
            name=op.f("ck_document_approval_settings_settings_key_supported"),
        ),
        sa.CheckConstraint(
            "schema_version = 1",
            name=op.f("ck_document_approval_settings_schema_version_supported"),
        ),
        sa.CheckConstraint(
            "required_approvals in (1, 2)",
            name=op.f("ck_document_approval_settings_required_approvals_supported"),
        ),
        sa.CheckConstraint(
            "length(trim(updated_by_actor_id)) > 0",
            name=op.f("ck_document_approval_settings_updated_by_actor_id_not_empty"),
        ),
        sa.PrimaryKeyConstraint(
            "settings_key",
            name=op.f("pk_document_approval_settings"),
        ),
    )


def downgrade() -> None:
    connection = op.get_bind()
    saved_settings = int(
        connection.scalar(sa.text("select count(*) from document_approval_settings")) or 0
    )
    one_reviewer_workflows = int(
        connection.scalar(
            sa.text(
                "select count(*) from document_approval_workflows where required_approvals <> 2"
            )
        )
        or 0
    )
    if saved_settings or one_reviewer_workflows:
        raise RuntimeError(
            "Cannot downgrade document approval settings while saved configuration "
            "or one-reviewer workflows exist."
        )
    op.drop_table("document_approval_settings")
    op.drop_constraint(
        op.f("ck_document_approval_workflows_required_approvals_supported"),
        "document_approval_workflows",
        type_="check",
    )
    op.drop_column("document_approval_workflows", "required_approvals")
