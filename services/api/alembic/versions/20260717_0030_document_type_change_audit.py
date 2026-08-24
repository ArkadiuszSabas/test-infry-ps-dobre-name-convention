"""Create immutable audit records for document type changes.

Revision ID: 20260721_0032
Revises: 20260717_0030
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260721_0032"
down_revision = "20260717_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_type_change_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_document_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("new_document_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", sa.String(length=200), nullable=False),
        sa.Column("reason", sa.String(length=2000), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(actor_id)) > 0", name="actor_id_not_empty"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["old_document_type_id"], ["document_types.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["new_document_type_id"], ["document_types.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_type_change_audit_events_document_id",
        "document_type_change_audit_events",
        ["document_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    audit_count = bind.execute(
        sa.text("select count(*) from document_type_change_audit_events")
    ).scalar_one()
    if audit_count:
        raise RuntimeError(
            "Cannot downgrade document type change audit migration while audit events exist."
        )
    op.drop_index(
        "ix_document_type_change_audit_events_document_id",
        table_name="document_type_change_audit_events",
    )
    op.drop_table("document_type_change_audit_events")
