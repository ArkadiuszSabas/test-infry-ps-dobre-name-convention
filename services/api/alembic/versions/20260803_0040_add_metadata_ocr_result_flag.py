"""Add the metadata-to-OCR-result configuration flag.

Revision ID: 20260803_0040
Revises: 20260731_0039
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260803_0040"
down_revision: str | Sequence[str] | None = "20260731_0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "attribute_requirements",
        sa.Column(
            "include_metadata_in_ocr_result",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column(
        "attribute_requirements",
        "include_metadata_in_ocr_result",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("attribute_requirements", "include_metadata_in_ocr_result")
