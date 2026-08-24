"""Create global OCR confidence color settings.

Revision ID: 20260728_0034
Revises: 20260727_0033
Create Date: 2026-07-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260728_0034"
down_revision: str | Sequence[str] | None = "20260727_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the singleton settings table without coupling it to pipeline versions."""

    op.create_table(
        "ocr_confidence_color_settings",
        sa.Column("settings_key", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("bands", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by_actor_id", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "jsonb_typeof(bands) = 'array'",
            name=op.f("ck_ocr_confidence_color_settings_bands_array"),
        ),
        sa.CheckConstraint(
            "jsonb_array_length(bands) between 1 and 5",
            name=op.f("ck_ocr_confidence_color_settings_bands_count_supported"),
        ),
        sa.CheckConstraint(
            "schema_version = 1",
            name=op.f("ck_ocr_confidence_color_settings_schema_version_supported"),
        ),
        sa.CheckConstraint(
            "settings_key = 'default'",
            name=op.f("ck_ocr_confidence_color_settings_settings_key_supported"),
        ),
        sa.CheckConstraint(
            "updated_by_actor_id is null or length(trim(updated_by_actor_id)) > 0",
            name=op.f("ck_ocr_confidence_color_settings_updated_by_actor_id_not_empty"),
        ),
        sa.PrimaryKeyConstraint(
            "settings_key",
            name=op.f("pk_ocr_confidence_color_settings"),
        ),
    )


def downgrade() -> None:
    """Remove the table only before an administrator saves configuration."""

    connection = op.get_bind()
    row_count = int(
        connection.scalar(sa.text("select count(*) from ocr_confidence_color_settings")) or 0
    )
    if row_count:
        raise RuntimeError(
            "Cannot downgrade OCR confidence color settings while saved configuration exists."
        )
    op.drop_table("ocr_confidence_color_settings")
