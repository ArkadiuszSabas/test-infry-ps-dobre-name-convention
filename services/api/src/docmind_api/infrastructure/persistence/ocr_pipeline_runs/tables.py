"""SQLAlchemy tables for OCR pipeline run persistence."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from docmind_api.domain.ocr_pipeline_runs.models import (
    OCR_PIPELINE_RUN_ACTOR_ID_MAX_LENGTH,
    OCR_PIPELINE_RUN_ACTOR_LOGIN_MAX_LENGTH,
    OCR_PIPELINE_RUN_CATALOG_VALUE_MAX_LENGTH,
    OCR_PIPELINE_RUN_CONNECTOR_VALUE_MAX_LENGTH,
    OCR_PIPELINE_RUN_DOCUMENT_REFERENCE_MAX_LENGTH,
    OCR_PIPELINE_RUN_ERROR_CODE_MAX_LENGTH,
)
from docmind_api.infrastructure.persistence.metadata import metadata

ocr_pipeline_runs_table = Table(
    "ocr_pipeline_runs",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "pipeline_id",
        UUID(as_uuid=True),
        ForeignKey("ocr_pipeline_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("pipeline_version", Integer, nullable=False),
    Column(
        "document_reference",
        String(length=OCR_PIPELINE_RUN_DOCUMENT_REFERENCE_MAX_LENGTH),
        nullable=False,
    ),
    Column("status", String(length=32), nullable=False),
    Column("compiled_snapshot", JSONB, nullable=False),
    Column(
        "catalog_version", String(length=OCR_PIPELINE_RUN_CATALOG_VALUE_MAX_LENGTH), nullable=True
    ),
    Column("catalog_hash", String(length=OCR_PIPELINE_RUN_CATALOG_VALUE_MAX_LENGTH), nullable=True),
    Column("steps", JSONB, nullable=False),
    Column("metrics", JSONB, nullable=False),
    Column("diagnostics", JSONB, nullable=False),
    Column("error", JSONB(none_as_null=True), nullable=True),
    Column("result_payload", JSONB(none_as_null=True), nullable=True),
    # Kept solely for compatibility with the already-applied 0041 migration.
    # Context Resolver metadata is intentionally not persisted as an OCR result.
    Column("metadata_snapshot", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column(
        "started_by_actor_id", String(length=OCR_PIPELINE_RUN_ACTOR_ID_MAX_LENGTH), nullable=True
    ),
    Column("started_by_actor_type", String(length=16), nullable=False),
    Column(
        "started_by_actor_login",
        String(length=OCR_PIPELINE_RUN_ACTOR_LOGIN_MAX_LENGTH),
        nullable=True,
    ),
    Column(
        "document_source",
        String(length=OCR_PIPELINE_RUN_CONNECTOR_VALUE_MAX_LENGTH),
        nullable=True,
    ),
    Column(
        "document_connector",
        String(length=OCR_PIPELINE_RUN_CONNECTOR_VALUE_MAX_LENGTH),
        nullable=True,
    ),
    Column(
        "connector_instance_id",
        String(length=OCR_PIPELINE_RUN_CONNECTOR_VALUE_MAX_LENGTH),
        nullable=True,
    ),
    Column(
        "connector_display_name",
        String(length=OCR_PIPELINE_RUN_CONNECTOR_VALUE_MAX_LENGTH),
        nullable=True,
    ),
    Column(
        "connector_correlation_id",
        String(length=OCR_PIPELINE_RUN_CONNECTOR_VALUE_MAX_LENGTH),
        nullable=True,
    ),
    CheckConstraint("pipeline_version > 0", name="pipeline_version_positive"),
    CheckConstraint("length(trim(document_reference)) > 0", name="document_reference_not_empty"),
    CheckConstraint(
        "status in ('pending', 'running', 'succeeded', 'partial_failed', 'failed')",
        name="status_supported",
    ),
    CheckConstraint("jsonb_typeof(compiled_snapshot) = 'object'", name="compiled_snapshot_object"),
    CheckConstraint("jsonb_typeof(steps) = 'array'", name="steps_array"),
    CheckConstraint("jsonb_typeof(metrics) = 'object'", name="metrics_object"),
    CheckConstraint("jsonb_typeof(diagnostics) = 'array'", name="diagnostics_array"),
    CheckConstraint("jsonb_typeof(metadata_snapshot) = 'array'", name="metadata_snapshot_array"),
    CheckConstraint("error is null or jsonb_typeof(error) = 'object'", name="error_object"),
    CheckConstraint(
        "result_payload is null or jsonb_typeof(result_payload) = 'object'",
        name="result_payload_object",
    ),
    CheckConstraint(
        "catalog_version is null or length(trim(catalog_version)) > 0",
        name="catalog_version_not_empty",
    ),
    CheckConstraint(
        "catalog_hash is null or length(trim(catalog_hash)) > 0",
        name="catalog_hash_not_empty",
    ),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    CheckConstraint(
        "started_at is null or created_at <= started_at",
        name="started_at_not_before_created_at",
    ),
    CheckConstraint(
        "completed_at is null or started_at is not null",
        name="completed_requires_started_at",
    ),
    CheckConstraint(
        "completed_at is null or started_at <= completed_at",
        name="completed_at_not_before_started_at",
    ),
    CheckConstraint(
        "started_by_actor_id is null or length(trim(started_by_actor_id)) > 0",
        name="started_by_actor_id_not_empty",
    ),
    CheckConstraint(
        "started_by_actor_type in ('human', 'connector', 'system')",
        name="started_by_actor_type_supported",
    ),
    CheckConstraint(
        "started_by_actor_login is null or length(trim(started_by_actor_login)) > 0",
        name="started_by_actor_login_not_empty",
    ),
    CheckConstraint(
        "started_by_actor_type = 'human' or started_by_actor_login is null",
        name="started_by_actor_login_human_only",
    ),
    CheckConstraint(
        "(started_by_actor_type = 'human' and started_by_actor_id is not null) "
        "or (started_by_actor_type = 'connector' "
        "and started_by_actor_id like 'connector:%') "
        "or started_by_actor_type = 'system'",
        name="started_by_actor_identity_valid",
    ),
    ForeignKeyConstraint(
        ["pipeline_id", "pipeline_version"],
        [
            "ocr_pipeline_definition_versions.definition_id",
            "ocr_pipeline_definition_versions.version_number",
        ],
        name="fk_ocr_pipeline_runs_pipeline_version",
        ondelete="RESTRICT",
    ),
    Index("ix_ocr_pipeline_runs_document_id", "document_id"),
    Index(
        "uq_ocr_pipeline_runs_active_document_id",
        "document_id",
        unique=True,
        postgresql_where=text("status in ('pending', 'running')"),
    ),
    Index("ix_ocr_pipeline_runs_pipeline_id", "pipeline_id"),
    Index("ix_ocr_pipeline_runs_status", "status"),
    Index("ix_ocr_pipeline_runs_created_at", "created_at"),
    Index("ix_ocr_pipeline_runs_completed_at", "completed_at"),
    Index("ix_ocr_pipeline_runs_document_created_at", "document_id", "created_at"),
)

ocr_pipeline_run_attempts_table = Table(
    "ocr_pipeline_run_attempts",
    metadata,
    Column("attempt_id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column(
        "run_id",
        UUID(as_uuid=True),
        ForeignKey("ocr_pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("owner_token", UUID(as_uuid=True), nullable=False),
    Column("attempt_number", Integer, nullable=False),
    Column("fencing_token", BigInteger, nullable=False),
    Column("status", String(length=32), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("invocation_started_at", DateTime(timezone=True), nullable=True),
    Column("last_renewed_at", DateTime(timezone=True), nullable=False),
    Column("lease_expires_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("error_code", String(length=OCR_PIPELINE_RUN_ERROR_CODE_MAX_LENGTH), nullable=True),
    CheckConstraint("attempt_number > 0", name="attempt_number_positive"),
    CheckConstraint("fencing_token > 0", name="fencing_token_positive"),
    CheckConstraint(
        "status in ('running', 'succeeded', 'partial_failed', 'failed', 'indeterminate', 'lost')",
        name="status_supported",
    ),
    CheckConstraint("started_at <= last_renewed_at", name="renewed_at_not_before_started_at"),
    CheckConstraint(
        "invocation_started_at is null or started_at <= invocation_started_at",
        name="invocation_not_before_started_at",
    ),
    CheckConstraint(
        "last_renewed_at < lease_expires_at",
        name="lease_expires_after_renewal",
    ),
    CheckConstraint(
        "completed_at is null or started_at <= completed_at",
        name="completed_at_not_before_started_at",
    ),
    CheckConstraint(
        "(status = 'running' and completed_at is null) "
        "or (status <> 'running' and completed_at is not null)",
        name="completion_matches_status",
    ),
    CheckConstraint(
        "error_code is null or length(trim(error_code)) > 0",
        name="error_code_not_empty",
    ),
    Index("ix_ocr_pipeline_run_attempts_run_id", "run_id"),
    Index(
        "uq_ocr_pipeline_run_attempts_run_attempt_number",
        "run_id",
        "attempt_number",
        unique=True,
    ),
    Index(
        "uq_ocr_pipeline_run_attempts_run_fencing_token",
        "run_id",
        "fencing_token",
        unique=True,
    ),
    Index(
        "uq_ocr_pipeline_run_attempts_active_run_id",
        "run_id",
        unique=True,
        postgresql_where=text("status = 'running'"),
    ),
    Index("ix_ocr_pipeline_run_attempts_lease_expires_at", "lease_expires_at"),
)
