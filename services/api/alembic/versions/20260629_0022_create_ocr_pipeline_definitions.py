"""Create OCR pipeline definition persistence.

Revision ID: 20260629_0022
Revises: 20260625_0021
Create Date: 2026-06-29 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260629_0022"
down_revision: str | None = "20260625_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAME_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 2000
ACTOR_ID_MAX_LENGTH = 128
CATALOG_VALUE_MAX_LENGTH = 256
AUDIT_ACTION_MAX_LENGTH = 64


def upgrade() -> None:
    """Create OCR pipeline definition, version, name, and audit tables."""

    op.create_table(
        "ocr_pipeline_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=NAME_MAX_LENGTH), nullable=False),
        sa.Column("description", sa.String(length=DESCRIPTION_MAX_LENGTH), nullable=True),
        sa.Column("lifecycle", sa.String(length=32), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("published_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_actor_id", sa.String(length=ACTOR_ID_MAX_LENGTH), nullable=True),
        sa.Column("updated_by_actor_id", sa.String(length=ACTOR_ID_MAX_LENGTH), nullable=True),
        sa.Column("published_by_actor_id", sa.String(length=ACTOR_ID_MAX_LENGTH), nullable=True),
        sa.Column("archived_by_actor_id", sa.String(length=ACTOR_ID_MAX_LENGTH), nullable=True),
        sa.Column(
            "default_set_by_actor_id",
            sa.String(length=ACTOR_ID_MAX_LENGTH),
            nullable=True,
        ),
        sa.CheckConstraint(
            "length(trim(display_name)) > 0",
            name=op.f("ck_ocr_pipeline_definitions_display_name_not_empty"),
        ),
        sa.CheckConstraint(
            "description is null or length(trim(description)) > 0",
            name=op.f("ck_ocr_pipeline_definitions_description_not_empty"),
        ),
        sa.CheckConstraint(
            "lifecycle in ('draft', 'published', 'archived')",
            name=op.f("ck_ocr_pipeline_definitions_lifecycle_supported"),
        ),
        sa.CheckConstraint(
            "published_version is null or published_version > 0",
            name=op.f("ck_ocr_pipeline_definitions_published_version_positive"),
        ),
        sa.CheckConstraint(
            "(lifecycle = 'draft' and published_version is null) or "
            "(lifecycle in ('published', 'archived') and published_version is not null)",
            name=op.f("ck_ocr_pipeline_definitions_published_version_matches_lifecycle"),
        ),
        sa.CheckConstraint(
            "is_default = false or (lifecycle = 'published' and published_version is not null)",
            name=op.f("ck_ocr_pipeline_definitions_default_requires_published_active_definition"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_ocr_pipeline_definitions_updated_at_not_before_created_at"),
        ),
        sa.CheckConstraint(
            "published_at is null or created_at <= published_at",
            name=op.f("ck_ocr_pipeline_definitions_published_at_not_before_created_at"),
        ),
        sa.CheckConstraint(
            "archived_at is null or published_at is not null",
            name=op.f("ck_ocr_pipeline_definitions_archived_requires_publish_time"),
        ),
        sa.CheckConstraint(
            "created_by_actor_id is null or length(trim(created_by_actor_id)) > 0",
            name=op.f("ck_ocr_pipeline_definitions_created_by_actor_id_not_empty"),
        ),
        sa.CheckConstraint(
            "updated_by_actor_id is null or length(trim(updated_by_actor_id)) > 0",
            name=op.f("ck_ocr_pipeline_definitions_updated_by_actor_id_not_empty"),
        ),
        sa.CheckConstraint(
            "published_by_actor_id is null or length(trim(published_by_actor_id)) > 0",
            name=op.f("ck_ocr_pipeline_definitions_published_by_actor_id_not_empty"),
        ),
        sa.CheckConstraint(
            "archived_by_actor_id is null or length(trim(archived_by_actor_id)) > 0",
            name=op.f("ck_ocr_pipeline_definitions_archived_by_actor_id_not_empty"),
        ),
        sa.CheckConstraint(
            "default_set_by_actor_id is null or length(trim(default_set_by_actor_id)) > 0",
            name=op.f("ck_ocr_pipeline_definitions_default_set_by_actor_id_not_empty"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ocr_pipeline_definitions")),
    )
    op.create_index(
        "ix_ocr_pipeline_definitions_lifecycle",
        "ocr_pipeline_definitions",
        ["lifecycle"],
    )
    op.create_index(
        "ix_ocr_pipeline_definitions_is_default",
        "ocr_pipeline_definitions",
        ["is_default"],
    )
    op.create_index(
        "uq_ocr_pipeline_definitions_single_default",
        "ocr_pipeline_definitions",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default is true"),
    )

    op.create_table(
        "ocr_pipeline_definition_versions",
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("definition_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "compiled_snapshot",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column(
            "validation_result",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column("catalog_version", sa.String(length=CATALOG_VALUE_MAX_LENGTH), nullable=True),
        sa.Column("catalog_hash", sa.String(length=CATALOG_VALUE_MAX_LENGTH), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_actor_id", sa.String(length=ACTOR_ID_MAX_LENGTH), nullable=True),
        sa.Column("updated_by_actor_id", sa.String(length=ACTOR_ID_MAX_LENGTH), nullable=True),
        sa.Column("published_by_actor_id", sa.String(length=ACTOR_ID_MAX_LENGTH), nullable=True),
        sa.CheckConstraint(
            "version_number >= 0",
            name=op.f("ck_ocr_pipeline_definition_versions_version_number_non_negative"),
        ),
        sa.CheckConstraint(
            "status in ('draft', 'published')",
            name=op.f("ck_ocr_pipeline_definition_versions_status_supported"),
        ),
        sa.CheckConstraint(
            "(status = 'draft' and version_number = 0 and published_at is null) or "
            "(status = 'published' and version_number > 0 and published_at is not null)",
            name=op.f("ck_ocr_pipeline_definition_versions_version_number_matches_status"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(definition_json) = 'object'",
            name=op.f("ck_ocr_pipeline_definition_versions_definition_json_object"),
        ),
        sa.CheckConstraint(
            "compiled_snapshot is null or jsonb_typeof(compiled_snapshot) = 'object'",
            name=op.f("ck_ocr_pipeline_definition_versions_compiled_snapshot_object"),
        ),
        sa.CheckConstraint(
            "validation_result is null or jsonb_typeof(validation_result) = 'object'",
            name=op.f("ck_ocr_pipeline_definition_versions_validation_result_object"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_ocr_pipeline_definition_versions_updated_at_not_before_created_at"),
        ),
        sa.CheckConstraint(
            "created_by_actor_id is null or length(trim(created_by_actor_id)) > 0",
            name=op.f("ck_ocr_pipeline_definition_versions_created_by_actor_id_not_empty"),
        ),
        sa.CheckConstraint(
            "updated_by_actor_id is null or length(trim(updated_by_actor_id)) > 0",
            name=op.f("ck_ocr_pipeline_definition_versions_updated_by_actor_id_not_empty"),
        ),
        sa.CheckConstraint(
            "published_by_actor_id is null or length(trim(published_by_actor_id)) > 0",
            name=op.f("ck_ocr_pipeline_definition_versions_published_by_actor_id_not_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            ["ocr_pipeline_definitions.id"],
            name=op.f("fk_ocr_pipeline_definition_versions_definition_id_ocr_pipeline_definitions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "definition_id",
            "version_number",
            name=op.f("pk_ocr_pipeline_definition_versions"),
        ),
    )
    op.create_index(
        "ix_ocr_pipeline_definition_versions_status",
        "ocr_pipeline_definition_versions",
        ["status"],
    )

    op.create_table(
        "ocr_pipeline_definition_names",
        sa.Column("normalized_name", sa.String(length=NAME_MAX_LENGTH), nullable=False),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=NAME_MAX_LENGTH), nullable=False),
        sa.CheckConstraint(
            "length(trim(normalized_name)) > 0",
            name=op.f("ck_ocr_pipeline_definition_names_normalized_name_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(display_name)) > 0",
            name=op.f("ck_ocr_pipeline_definition_names_display_name_not_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["definition_id"],
            ["ocr_pipeline_definitions.id"],
            name=op.f("fk_ocr_pipeline_definition_names_definition_id_ocr_pipeline_definitions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("normalized_name", name=op.f("pk_ocr_pipeline_definition_names")),
    )
    op.create_index(
        "ix_ocr_pipeline_definition_names_definition_id",
        "ocr_pipeline_definition_names",
        ["definition_id"],
    )

    op.create_table(
        "ocr_pipeline_definition_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=AUDIT_ACTION_MAX_LENGTH), nullable=False),
        sa.Column("actor_id", sa.String(length=ACTOR_ID_MAX_LENGTH), nullable=True),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "action in ('created', 'draft_updated', 'validated', 'published', 'archived', "
            "'deleted', 'default_changed')",
            name=op.f("ck_ocr_pipeline_definition_audit_events_action_supported"),
        ),
        sa.CheckConstraint(
            "actor_id is null or length(trim(actor_id)) > 0",
            name=op.f("ck_ocr_pipeline_definition_audit_events_actor_id_not_empty"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(details) = 'object'",
            name=op.f("ck_ocr_pipeline_definition_audit_events_details_object"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ocr_pipeline_definition_audit_events")),
    )
    op.create_index(
        "ix_ocr_pipeline_definition_audit_events_pipeline_id",
        "ocr_pipeline_definition_audit_events",
        ["pipeline_id"],
    )
    op.create_index(
        "ix_ocr_pipeline_definition_audit_events_event_at",
        "ocr_pipeline_definition_audit_events",
        ["event_at"],
    )


def downgrade() -> None:
    """Remove OCR pipeline definition persistence after an empty-state guard."""

    _guard_safe_ocr_pipeline_downgrade(op.get_bind())

    op.drop_index(
        "ix_ocr_pipeline_definition_audit_events_event_at",
        table_name="ocr_pipeline_definition_audit_events",
    )
    op.drop_index(
        "ix_ocr_pipeline_definition_audit_events_pipeline_id",
        table_name="ocr_pipeline_definition_audit_events",
    )
    op.drop_table("ocr_pipeline_definition_audit_events")
    op.drop_index(
        "ix_ocr_pipeline_definition_names_definition_id",
        table_name="ocr_pipeline_definition_names",
    )
    op.drop_table("ocr_pipeline_definition_names")
    op.drop_index(
        "ix_ocr_pipeline_definition_versions_status",
        table_name="ocr_pipeline_definition_versions",
    )
    op.drop_table("ocr_pipeline_definition_versions")
    op.drop_index(
        "uq_ocr_pipeline_definitions_single_default",
        table_name="ocr_pipeline_definitions",
        postgresql_where=sa.text("is_default is true"),
    )
    op.drop_index("ix_ocr_pipeline_definitions_is_default", table_name="ocr_pipeline_definitions")
    op.drop_index("ix_ocr_pipeline_definitions_lifecycle", table_name="ocr_pipeline_definitions")
    op.drop_table("ocr_pipeline_definitions")


def _guard_safe_ocr_pipeline_downgrade(connection: Connection) -> None:
    """Block downgrade once OCR pipeline configuration or audit state exists."""

    unsafe_tables: list[str] = []
    for table_name in (
        "ocr_pipeline_definition_audit_events",
        "ocr_pipeline_definition_names",
        "ocr_pipeline_definition_versions",
        "ocr_pipeline_definitions",
    ):
        row_count = int(connection.scalar(sa.text(f"select count(*) from {table_name}")) or 0)
        if row_count:
            unsafe_tables.append(f"{table_name}={row_count}")

    if unsafe_tables:
        raise RuntimeError(
            "Cannot downgrade OCR pipeline definition persistence while pipeline state exists: "
            f"{', '.join(unsafe_tables)}.",
        )
