"""Add optional LLM context to attribute definitions.

Revision ID: 20260714_0028
Revises: 20260708_0027
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260714_0028"
down_revision: str | Sequence[str] | None = "20260708_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "attribute_definitions",
        sa.Column("llm_context", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "llm_context_not_empty",
        "attribute_definitions",
        "llm_context is null or length(trim(llm_context)) > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "llm_context_not_empty",
        "attribute_definitions",
        type_="check",
    )
    op.drop_column("attribute_definitions", "llm_context")
