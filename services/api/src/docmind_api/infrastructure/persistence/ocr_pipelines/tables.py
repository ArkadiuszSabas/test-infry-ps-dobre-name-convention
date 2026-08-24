"""SQLAlchemy tables for OCR pipeline definition persistence."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from docmind_api.domain.ocr_pipelines.models import (
    OCR_PIPELINE_DESCRIPTION_MAX_LENGTH,
    OCR_PIPELINE_NAME_MAX_LENGTH,
)
from docmind_api.infrastructure.persistence.metadata import metadata

OCR_PIPELINE_ACTOR_ID_MAX_LENGTH = 128
OCR_PIPELINE_CATALOG_VALUE_MAX_LENGTH = 256
OCR_PIPELINE_AUDIT_ACTION_MAX_LENGTH = 64
OCR_CONFIDENCE_COLOR_SETTINGS_KEY_MAX_LENGTH = 64

ocr_pipeline_definitions_table = Table(
    "ocr_pipeline_definitions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("display_name", String(length=OCR_PIPELINE_NAME_MAX_LENGTH), nullable=False),
    Column(
        "description",
        String(length=OCR_PIPELINE_DESCRIPTION_MAX_LENGTH),
        nullable=True,
    ),
    Column("lifecycle", String(length=32), nullable=False),
    Column("is_default", Boolean, nullable=False),
    Column("published_version", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("published_at", DateTime(timezone=True), nullable=True),
    Column("archived_at", DateTime(timezone=True), nullable=True),
    Column("created_by_actor_id", String(length=OCR_PIPELINE_ACTOR_ID_MAX_LENGTH), nullable=True),
    Column("updated_by_actor_id", String(length=OCR_PIPELINE_ACTOR_ID_MAX_LENGTH), nullable=True),
    Column("published_by_actor_id", String(length=OCR_PIPELINE_ACTOR_ID_MAX_LENGTH), nullable=True),
    Column("archived_by_actor_id", String(length=OCR_PIPELINE_ACTOR_ID_MAX_LENGTH), nullable=True),
    Column(
        "default_set_by_actor_id",
        String(length=OCR_PIPELINE_ACTOR_ID_MAX_LENGTH),
        nullable=True,
    ),
    CheckConstraint("length(trim(display_name)) > 0", name="display_name_not_empty"),
    CheckConstraint(
        "description is null or length(trim(description)) > 0",
        name="description_not_empty",
    ),
    CheckConstraint(
        "lifecycle in ('draft', 'published', 'archived')",
        name="lifecycle_supported",
    ),
    CheckConstraint(
        "published_version is null or published_version > 0",
        name="published_version_positive",
    ),
    CheckConstraint(
        "(lifecycle = 'draft' and published_version is null) or "
        "(lifecycle in ('published', 'archived') and published_version is not null)",
        name="published_version_matches_lifecycle",
    ),
    CheckConstraint(
        "is_default = false or (lifecycle = 'published' and published_version is not null)",
        name="default_requires_published_active_definition",
    ),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    CheckConstraint(
        "published_at is null or created_at <= published_at",
        name="published_at_not_before_created_at",
    ),
    CheckConstraint(
        "archived_at is null or published_at is not null",
        name="archived_requires_publish_time",
    ),
    CheckConstraint(
        "created_by_actor_id is null or length(trim(created_by_actor_id)) > 0",
        name="created_by_actor_id_not_empty",
    ),
    CheckConstraint(
        "updated_by_actor_id is null or length(trim(updated_by_actor_id)) > 0",
        name="updated_by_actor_id_not_empty",
    ),
    CheckConstraint(
        "published_by_actor_id is null or length(trim(published_by_actor_id)) > 0",
        name="published_by_actor_id_not_empty",
    ),
    CheckConstraint(
        "archived_by_actor_id is null or length(trim(archived_by_actor_id)) > 0",
        name="archived_by_actor_id_not_empty",
    ),
    CheckConstraint(
        "default_set_by_actor_id is null or length(trim(default_set_by_actor_id)) > 0",
        name="default_set_by_actor_id_not_empty",
    ),
    Index("ix_ocr_pipeline_definitions_lifecycle", "lifecycle"),
    Index("ix_ocr_pipeline_definitions_is_default", "is_default"),
    Index(
        "uq_ocr_pipeline_definitions_single_default",
        "is_default",
        unique=True,
        postgresql_where=text("is_default is true"),
    ),
)

ocr_pipeline_definition_versions_table = Table(
    "ocr_pipeline_definition_versions",
    metadata,
    Column(
        "definition_id",
        UUID(as_uuid=True),
        ForeignKey("ocr_pipeline_definitions.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column("version_number", Integer, primary_key=True, nullable=False),
    Column("status", String(length=32), nullable=False),
    Column("definition_json", JSONB, nullable=False),
    Column("compiled_snapshot", JSONB(none_as_null=True), nullable=True),
    Column("validation_result", JSONB(none_as_null=True), nullable=True),
    Column("catalog_version", String(length=OCR_PIPELINE_CATALOG_VALUE_MAX_LENGTH), nullable=True),
    Column("catalog_hash", String(length=OCR_PIPELINE_CATALOG_VALUE_MAX_LENGTH), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("published_at", DateTime(timezone=True), nullable=True),
    Column("created_by_actor_id", String(length=OCR_PIPELINE_ACTOR_ID_MAX_LENGTH), nullable=True),
    Column("updated_by_actor_id", String(length=OCR_PIPELINE_ACTOR_ID_MAX_LENGTH), nullable=True),
    Column("published_by_actor_id", String(length=OCR_PIPELINE_ACTOR_ID_MAX_LENGTH), nullable=True),
    CheckConstraint("version_number >= 0", name="version_number_non_negative"),
    CheckConstraint("status in ('draft', 'published')", name="status_supported"),
    CheckConstraint(
        "(status = 'draft' and version_number = 0 and published_at is null) or "
        "(status = 'published' and version_number > 0 and published_at is not null)",
        name="version_number_matches_status",
    ),
    CheckConstraint("jsonb_typeof(definition_json) = 'object'", name="definition_json_object"),
    CheckConstraint(
        "compiled_snapshot is null or jsonb_typeof(compiled_snapshot) = 'object'",
        name="compiled_snapshot_object",
    ),
    CheckConstraint(
        "validation_result is null or jsonb_typeof(validation_result) = 'object'",
        name="validation_result_object",
    ),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    CheckConstraint(
        "created_by_actor_id is null or length(trim(created_by_actor_id)) > 0",
        name="created_by_actor_id_not_empty",
    ),
    CheckConstraint(
        "updated_by_actor_id is null or length(trim(updated_by_actor_id)) > 0",
        name="updated_by_actor_id_not_empty",
    ),
    CheckConstraint(
        "published_by_actor_id is null or length(trim(published_by_actor_id)) > 0",
        name="published_by_actor_id_not_empty",
    ),
    Index("ix_ocr_pipeline_definition_versions_status", "status"),
)

ocr_pipeline_definition_names_table = Table(
    "ocr_pipeline_definition_names",
    metadata,
    Column("normalized_name", String(length=OCR_PIPELINE_NAME_MAX_LENGTH), primary_key=True),
    Column(
        "definition_id",
        UUID(as_uuid=True),
        ForeignKey("ocr_pipeline_definitions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("display_name", String(length=OCR_PIPELINE_NAME_MAX_LENGTH), nullable=False),
    CheckConstraint("length(trim(normalized_name)) > 0", name="normalized_name_not_empty"),
    CheckConstraint("length(trim(display_name)) > 0", name="display_name_not_empty"),
    Index("ix_ocr_pipeline_definition_names_definition_id", "definition_id"),
)

ocr_pipeline_definition_audit_events_table = Table(
    "ocr_pipeline_definition_audit_events",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("pipeline_id", UUID(as_uuid=True), nullable=False),
    Column("action", String(length=OCR_PIPELINE_AUDIT_ACTION_MAX_LENGTH), nullable=False),
    Column("actor_id", String(length=OCR_PIPELINE_ACTOR_ID_MAX_LENGTH), nullable=True),
    Column("event_at", DateTime(timezone=True), nullable=False),
    Column("details", JSONB, nullable=False),
    CheckConstraint(
        "action in ('created', 'draft_updated', 'validated', 'published', 'archived', "
        "'deleted', 'default_changed')",
        name="action_supported",
    ),
    CheckConstraint("actor_id is null or length(trim(actor_id)) > 0", name="actor_id_not_empty"),
    CheckConstraint("jsonb_typeof(details) = 'object'", name="details_object"),
    Index("ix_ocr_pipeline_definition_audit_events_pipeline_id", "pipeline_id"),
    Index("ix_ocr_pipeline_definition_audit_events_event_at", "event_at"),
)

ocr_confidence_color_settings_table = Table(
    "ocr_confidence_color_settings",
    metadata,
    Column(
        "settings_key",
        String(length=OCR_CONFIDENCE_COLOR_SETTINGS_KEY_MAX_LENGTH),
        primary_key=True,
        nullable=False,
    ),
    Column("schema_version", Integer, nullable=False),
    Column("bands", JSONB, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("updated_by_actor_id", String(length=OCR_PIPELINE_ACTOR_ID_MAX_LENGTH), nullable=True),
    CheckConstraint("settings_key = 'default'", name="settings_key_supported"),
    CheckConstraint("schema_version = 1", name="schema_version_supported"),
    CheckConstraint("jsonb_typeof(bands) = 'array'", name="bands_array"),
    CheckConstraint(
        "jsonb_array_length(bands) between 1 and 5",
        name="bands_count_supported",
    ),
    CheckConstraint(
        "updated_by_actor_id is null or length(trim(updated_by_actor_id)) > 0",
        name="updated_by_actor_id_not_empty",
    ),
)
