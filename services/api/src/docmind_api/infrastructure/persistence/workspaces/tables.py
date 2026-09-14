"""SQLAlchemy tables for shared workspace registry control records."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Table,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from docmind_api.infrastructure.persistence.metadata import metadata

workspaces_table = Table(
    "workspaces",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("directory_dictionary_id", UUID(as_uuid=True), nullable=True),
    Column(
        "directory_entry_id",
        UUID(as_uuid=True),
        nullable=True,
    ),
    Column("schema_name", String(length=63), nullable=False),
    Column("schema_layout", String(length=32), nullable=False),
    Column("storage_prefix", String(length=256), nullable=False),
    Column("lifecycle", String(length=32), nullable=False, server_default=text("'registered'")),
    Column("schema_state", String(length=32), nullable=False, server_default=text("'pending'")),
    Column("schema_revision", String(length=128), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "(directory_dictionary_id is null) = (directory_entry_id is null)",
        name="directory_binding_paired",
    ),
    CheckConstraint(
        "schema_name = 'ws_' || replace(id::text, '-', '')",
        name="schema_name_server_owned",
    ),
    CheckConstraint("schema_layout = 'dedicated_schema'", name="schema_layout_supported"),
    CheckConstraint(
        "storage_prefix = 'workspaces/' || id::text",
        name="storage_prefix_server_owned",
    ),
    CheckConstraint(
        "lifecycle in ('registered', 'active', 'suspended', 'deleting', 'deleted')",
        name="lifecycle_supported",
    ),
    CheckConstraint(
        "schema_state in ('pending', 'ready', 'failed')", name="schema_state_supported"
    ),
    CheckConstraint(
        "schema_state <> 'ready' or schema_revision is not null",
        name="ready_schema_has_revision",
    ),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    ForeignKeyConstraint(
        ["directory_entry_id", "directory_dictionary_id"],
        ["dictionary_entries.id", "dictionary_entries.dictionary_id"],
        name="fk_workspaces_directory_entry_id_dictionary_entries",
        ondelete="RESTRICT",
    ),
    Index("uq_workspaces_directory_entry_id", "directory_entry_id", unique=True),
    Index("uq_workspaces_schema_name", "schema_name", unique=True),
    Index("uq_workspaces_storage_prefix", "storage_prefix", unique=True),
    Index("ix_workspaces_lifecycle", "lifecycle"),
    Index("ix_workspaces_schema_state", "schema_state"),
)

workspace_provisioning_requests_table = Table(
    "workspace_provisioning_requests",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column(
        "workspace_id",
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("idempotency_key", String(length=128), nullable=False),
    Column("payload_fingerprint", String(length=64), nullable=False),
    Column("target_revision", String(length=128), nullable=False),
    Column("status", String(length=32), nullable=False, server_default=text("'pending'")),
    Column("result_code", String(length=128), nullable=True),
    Column("result_message", String(length=512), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    CheckConstraint("length(trim(idempotency_key)) > 0", name="idempotency_key_not_empty"),
    CheckConstraint("length(payload_fingerprint) = 64", name="payload_fingerprint_sha256"),
    CheckConstraint("status in ('pending', 'succeeded', 'failed')", name="status_supported"),
    CheckConstraint(
        "(status = 'pending' and completed_at is null) or "
        "(status in ('succeeded', 'failed') and completed_at is not null)",
        name="completion_matches_status",
    ),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    Index("uq_workspace_provisioning_requests_idempotency_key", "idempotency_key", unique=True),
    Index("ix_workspace_provisioning_requests_workspace_id", "workspace_id"),
    Index("ix_workspace_provisioning_requests_pending", "status", "created_at"),
)
