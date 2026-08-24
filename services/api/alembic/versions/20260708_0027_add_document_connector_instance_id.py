"""Add connector instance provenance to documents.

Revision ID: 20260708_0027
Revises: 20260703_0026
Create Date: 2026-07-08 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260708_0027"
down_revision: str | Sequence[str] | None = "20260703_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("connector_instance_id", sa.String(length=200), nullable=True),
    )
    op.create_check_constraint(
        "connector_instance_id_not_empty",
        "documents",
        "connector_instance_id is null or length(trim(connector_instance_id)) > 0",
    )
    op.create_index(
        "ix_documents_connector_instance_id",
        "documents",
        ["connector_instance_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_connector_instance_id", table_name="documents")
    op.drop_constraint(
        "connector_instance_id_not_empty",
        "documents",
        type_="check",
    )
    op.drop_column("documents", "connector_instance_id")
