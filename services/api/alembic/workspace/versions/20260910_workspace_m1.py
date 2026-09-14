"""Create the first empty operational schema for a registered workspace."""

from __future__ import annotations

from alembic import context, op

from docmind_api.infrastructure.persistence.workspaces.schema_baseline import (
    LOCAL_BASELINE_REVISION,
    create_workspace_schema_objects,
)

revision: str = LOCAL_BASELINE_REVISION
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create only the pinned local object set in the configured workspace schema."""

    schema_name = context.config.attributes.get("workspace_schema")
    if not isinstance(schema_name, str):
        raise RuntimeError("Workspace Alembic migration requires a configured workspace schema.")
    create_workspace_schema_objects(op.get_bind(), schema_name=schema_name)


def downgrade() -> None:
    raise RuntimeError("Workspace baselines are forward-only; use a reviewed repair or restore.")
