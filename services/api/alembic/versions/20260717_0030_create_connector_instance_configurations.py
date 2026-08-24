"""Create durable API-owned connector instance configuration.

Revision ID: 20260717_0030
Revises: 20260721_0031
Create Date: 2026-07-17 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260717_0030"
down_revision: str | Sequence[str] | None = "20260721_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "connector_instance_configurations",
        sa.Column("connector_instance_id", sa.String(length=160), nullable=False),
        sa.Column("values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("api_key_salt", sa.String(length=64), nullable=True),
        sa.Column("api_key_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(connector_instance_id)) > 0",
            name=op.f("ck_connector_instance_configurations_instance_id_not_empty"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(values) = 'object'",
            name=op.f("ck_connector_instance_configurations_values_object"),
        ),
        sa.CheckConstraint(
            "(api_key_salt is null and api_key_hash is null) "
            "or (api_key_salt is not null and api_key_hash is not null)",
            name=op.f("ck_connector_instance_configurations_api_key_complete"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_connector_instance_configurations_updated_at_not_before_created_at"),
        ),
        sa.PrimaryKeyConstraint(
            "connector_instance_id",
            name=op.f("pk_connector_instance_configurations"),
        ),
    )


def downgrade() -> None:
    op.drop_table("connector_instance_configurations")
