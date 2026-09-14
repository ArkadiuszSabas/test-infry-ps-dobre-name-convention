"""Create shared workspace registry and durable provisioning-request records.

Revision ID: 20260909_0051
Revises: 20260828_0050
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260909_0051"
down_revision: str | Sequence[str] | None = "20260828_0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create API-owned shared control records without provisioning any workspace schema."""

    op.create_unique_constraint(
        op.f("uq_dictionary_entries_id_dictionary_id"),
        "dictionary_entries",
        ["id", "dictionary_id"],
    )
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("directory_dictionary_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("directory_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("schema_name", sa.String(length=63), nullable=False),
        sa.Column("schema_layout", sa.String(length=32), nullable=False),
        sa.Column("storage_prefix", sa.String(length=256), nullable=False),
        sa.Column("lifecycle", sa.String(length=32), nullable=False),
        sa.Column("schema_state", sa.String(length=32), nullable=False),
        sa.Column("schema_revision", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(directory_dictionary_id is null) = (directory_entry_id is null)",
            name=op.f("ck_workspaces_directory_binding_paired"),
        ),
        sa.CheckConstraint(
            "schema_name = 'ws_' || replace(id::text, '-', '')",
            name=op.f("ck_workspaces_schema_name_server_owned"),
        ),
        sa.CheckConstraint(
            "schema_layout = 'dedicated_schema'",
            name=op.f("ck_workspaces_schema_layout_supported"),
        ),
        sa.CheckConstraint(
            "storage_prefix = 'workspaces/' || id::text",
            name=op.f("ck_workspaces_storage_prefix_server_owned"),
        ),
        sa.CheckConstraint(
            "lifecycle in ('registered', 'active', 'suspended', 'deleting', 'deleted')",
            name=op.f("ck_workspaces_lifecycle_supported"),
        ),
        sa.CheckConstraint(
            "schema_state in ('pending', 'ready', 'failed')",
            name=op.f("ck_workspaces_schema_state_supported"),
        ),
        sa.CheckConstraint(
            "schema_state <> 'ready' or schema_revision is not null",
            name=op.f("ck_workspaces_ready_schema_has_revision"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_workspaces_updated_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(
            ["directory_entry_id", "directory_dictionary_id"],
            ["dictionary_entries.id", "dictionary_entries.dictionary_id"],
            name=op.f("fk_workspaces_directory_entry_id_dictionary_entries"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
    )
    op.create_index(
        "uq_workspaces_directory_entry_id",
        "workspaces",
        ["directory_entry_id"],
        unique=True,
    )
    op.create_index("uq_workspaces_schema_name", "workspaces", ["schema_name"], unique=True)
    op.create_index(
        "uq_workspaces_storage_prefix",
        "workspaces",
        ["storage_prefix"],
        unique=True,
    )
    op.create_index("ix_workspaces_lifecycle", "workspaces", ["lifecycle"])
    op.create_index("ix_workspaces_schema_state", "workspaces", ["schema_state"])
    op.create_table(
        "workspace_provisioning_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("payload_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("target_revision", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result_code", sa.String(length=128), nullable=True),
        sa.Column("result_message", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name=op.f("ck_workspace_provisioning_requests_idempotency_key_not_empty"),
        ),
        sa.CheckConstraint(
            "length(payload_fingerprint) = 64",
            name=op.f("ck_workspace_provisioning_requests_payload_fingerprint_sha256"),
        ),
        sa.CheckConstraint(
            "status in ('pending', 'succeeded', 'failed')",
            name=op.f("ck_workspace_provisioning_requests_status_supported"),
        ),
        sa.CheckConstraint(
            "(status = 'pending' and completed_at is null) or "
            "(status in ('succeeded', 'failed') and completed_at is not null)",
            name=op.f("ck_workspace_provisioning_requests_completion_matches_status"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_workspace_provisioning_requests_updated_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_workspace_provisioning_requests_workspace_id_workspaces"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspace_provisioning_requests")),
    )
    op.create_index(
        "uq_workspace_provisioning_requests_idempotency_key",
        "workspace_provisioning_requests",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_workspace_provisioning_requests_workspace_id",
        "workspace_provisioning_requests",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_provisioning_requests_pending",
        "workspace_provisioning_requests",
        ["status", "created_at"],
    )


def downgrade() -> None:
    """Remove registry state only when it is provably unused."""

    _guard_empty_workspace_registry(op.get_bind())
    op.drop_index(
        "ix_workspace_provisioning_requests_pending", table_name="workspace_provisioning_requests"
    )
    op.drop_index(
        "ix_workspace_provisioning_requests_workspace_id",
        table_name="workspace_provisioning_requests",
    )
    op.drop_index(
        "uq_workspace_provisioning_requests_idempotency_key",
        table_name="workspace_provisioning_requests",
    )
    op.drop_table("workspace_provisioning_requests")
    op.drop_index("ix_workspaces_schema_state", table_name="workspaces")
    op.drop_index("ix_workspaces_lifecycle", table_name="workspaces")
    op.drop_index("uq_workspaces_storage_prefix", table_name="workspaces")
    op.drop_index("uq_workspaces_schema_name", table_name="workspaces")
    op.drop_index("uq_workspaces_directory_entry_id", table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_constraint(
        op.f("uq_dictionary_entries_id_dictionary_id"),
        "dictionary_entries",
        type_="unique",
    )


def _guard_empty_workspace_registry(connection: Connection) -> None:
    request_count = int(
        connection.scalar(sa.text("select count(*) from workspace_provisioning_requests")) or 0,
    )
    workspace_count = int(connection.scalar(sa.text("select count(*) from workspaces")) or 0)
    if request_count or workspace_count:
        raise RuntimeError(
            "Cannot downgrade workspace registry while control records exist: "
            f"workspaces={workspace_count}, requests={request_count}.",
        )
