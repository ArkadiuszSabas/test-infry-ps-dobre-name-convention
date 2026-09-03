"""SQLAlchemy tables for immutable document Review versions."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from docmind_api.infrastructure.persistence.metadata import metadata

document_reviews_table = Table(
    "document_reviews",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("current_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("current_version > 0", name="current_version_positive"),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    Index("uq_document_reviews_document_id", "document_id", unique=True),
)

document_review_versions_table = Table(
    "document_review_versions",
    metadata,
    Column(
        "review_id",
        UUID(as_uuid=True),
        ForeignKey("document_reviews.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column("version", Integer, primary_key=True, nullable=False),
    Column("data_source", String(length=32), nullable=False),
    Column("is_reprocessing", Boolean, nullable=False, server_default="false"),
    Column("pipeline_sources_hydrated", Boolean, nullable=False, server_default="false"),
    Column(
        "source_pipeline_run_id",
        UUID(as_uuid=True),
        ForeignKey("ocr_pipeline_runs.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("attributes", JSONB, nullable=False),
    Column("validations", JSONB, nullable=False),
    Column("quality_score", Float(), nullable=True),
    Column("created_by_actor_id", String(length=200), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("version > 0", name="version_positive"),
    CheckConstraint(
        "data_source in ('mock', 'pipeline', 'manual')",
        name="data_source_supported",
    ),
    CheckConstraint("jsonb_typeof(attributes) = 'array'", name="attributes_array"),
    CheckConstraint("jsonb_typeof(validations) = 'array'", name="validations_array"),
    CheckConstraint(
        "quality_score is null or (quality_score >= 0 and quality_score <= 1)",
        name="quality_score_range",
    ),
    CheckConstraint(
        "created_by_actor_id is null or length(trim(created_by_actor_id)) > 0",
        name="created_by_actor_id_not_empty",
    ),
    Index("ix_document_review_versions_source_pipeline_run_id", "source_pipeline_run_id"),
    Index("ix_document_review_versions_created_at", "created_at"),
)

document_reviews_table.append_constraint(
    ForeignKeyConstraint(
        ["id", "current_version"],
        ["document_review_versions.review_id", "document_review_versions.version"],
        name="fk_document_reviews_current_version",
        use_alter=True,
        deferrable=True,
        initially="DEFERRED",
    ),
)

document_approval_workflows_table = Table(
    "document_approval_workflows",
    metadata,
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Column("current_run", Integer, nullable=False),
    Column("review_version", Integer, nullable=False),
    Column("required_approvals", Integer, nullable=False, server_default="2"),
    Column("status", String(length=32), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("current_run > 0", name="current_run_positive"),
    CheckConstraint("review_version > 0", name="review_version_positive"),
    CheckConstraint(
        "required_approvals in (1, 2)",
        name="required_approvals_supported",
    ),
    CheckConstraint(
        "status in ('waiting_for_review', 'in_review', 'approved')",
        name="status_supported",
    ),
)

document_approval_settings_table = Table(
    "document_approval_settings",
    metadata,
    Column("settings_key", String(length=50), primary_key=True, nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("required_approvals", Integer, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("updated_by_actor_id", String(length=200), nullable=False),
    CheckConstraint(
        "settings_key = 'default'",
        name="settings_key_supported",
    ),
    CheckConstraint(
        "schema_version = 1",
        name="schema_version_supported",
    ),
    CheckConstraint(
        "required_approvals in (1, 2)",
        name="required_approvals_supported",
    ),
    CheckConstraint(
        "length(trim(updated_by_actor_id)) > 0",
        name="updated_by_actor_id_not_empty",
    ),
)

document_approval_decisions_table = Table(
    "document_approval_decisions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column(
        "document_id",
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("run_number", Integer, nullable=False),
    Column("step_number", Integer, nullable=False),
    Column("decision", String(length=16), nullable=False),
    Column("actor_id", String(length=200), nullable=False),
    Column("comment", String(length=2000), nullable=True),
    Column("decided_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("run_number > 0", name="run_number_positive"),
    CheckConstraint("step_number in (1, 2)", name="step_number_supported"),
    CheckConstraint("decision in ('approved', 'rejected')", name="decision_supported"),
    CheckConstraint("length(trim(actor_id)) > 0", name="actor_id_not_empty"),
    CheckConstraint("comment is null or length(trim(comment)) > 0", name="comment_not_empty"),
    CheckConstraint(
        "decision <> 'rejected' or comment is not null",
        name="rejection_comment_required",
    ),
    Index(
        "uq_document_approval_decisions_document_run_step",
        "document_id",
        "run_number",
        "step_number",
        unique=True,
    ),
)
