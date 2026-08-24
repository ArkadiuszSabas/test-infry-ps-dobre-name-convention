"""Constrain role assignment identity link ownership.

Revision ID: 20260528_0009
Revises: 20260528_0008
Create Date: 2026-05-28 00:09:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260528_0009"
down_revision: str | None = "20260528_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("fk_role_assignments_identity_link_id_identity_links"),
        "role_assignments",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_role_assignments_user_id_identity_links"),
        "role_assignments",
        "identity_links",
        ["user_id", "identity_link_id"],
        ["user_id", "id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_role_assignments_user_id_identity_links"),
        "role_assignments",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_role_assignments_identity_link_id_identity_links"),
        "role_assignments",
        "identity_links",
        ["identity_link_id"],
        ["id"],
    )
