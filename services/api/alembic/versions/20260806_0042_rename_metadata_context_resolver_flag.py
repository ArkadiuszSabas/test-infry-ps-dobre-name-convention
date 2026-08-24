"""Rename the metadata Context Resolver configuration flag.

Revision ID: 20260806_0042
Revises: 20260804_0041
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260806_0042"
down_revision: str | Sequence[str] | None = "20260804_0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "attribute_requirements"
_OLD_COLUMN_NAME = "include_metadata_in_ocr_result"
_NEW_COLUMN_NAME = "include_metadata_in_context_resolver"


def upgrade() -> None:
    op.alter_column(
        _TABLE_NAME,
        _OLD_COLUMN_NAME,
        new_column_name=_NEW_COLUMN_NAME,
    )


def downgrade() -> None:
    op.alter_column(
        _TABLE_NAME,
        _NEW_COLUMN_NAME,
        new_column_name=_OLD_COLUMN_NAME,
    )
