"""Create versioned document Review state.

Revision ID: 20260715_0029
Revises: 20260714_0028
Create Date: 2026-07-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260715_0029"
down_revision: str | Sequence[str] | None = "20260714_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "current_version > 0",
            name=op.f("ck_document_reviews_current_version_positive"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_document_reviews_updated_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_reviews")),
    )
    op.create_index(
        "uq_document_reviews_document_id",
        "document_reviews",
        ["document_id"],
        unique=True,
    )
    op.create_table(
        "document_review_versions",
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("data_source", sa.String(length=32), nullable=False),
        sa.Column("source_pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("created_by_actor_id", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "version > 0",
            name=op.f("ck_document_review_versions_version_positive"),
        ),
        sa.CheckConstraint(
            "data_source in ('mock', 'pipeline', 'manual')",
            name=op.f("ck_document_review_versions_data_source_supported"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(attributes) = 'array'",
            name=op.f("ck_document_review_versions_attributes_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(validations) = 'array'",
            name=op.f("ck_document_review_versions_validations_array"),
        ),
        sa.CheckConstraint(
            "quality_score is null or (quality_score >= 0 and quality_score <= 1)",
            name=op.f("ck_document_review_versions_quality_score_range"),
        ),
        sa.CheckConstraint(
            "created_by_actor_id is null or length(trim(created_by_actor_id)) > 0",
            name=op.f("ck_document_review_versions_created_by_actor_id_not_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["document_reviews.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_pipeline_run_id"],
            ["ocr_pipeline_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "review_id",
            "version",
            name=op.f("pk_document_review_versions"),
        ),
    )
    op.create_index(
        "ix_document_review_versions_created_at",
        "document_review_versions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_document_review_versions_source_pipeline_run_id",
        "document_review_versions",
        ["source_pipeline_run_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_document_reviews_current_version",
        "document_reviews",
        "document_review_versions",
        ["id", "current_version"],
        ["review_id", "version"],
        deferrable=True,
        initially="DEFERRED",
        use_alter=True,
    )


def downgrade() -> None:
    _guard_safe_document_review_downgrade(op.get_bind())

    op.drop_constraint(
        "fk_document_reviews_current_version",
        "document_reviews",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_document_review_versions_source_pipeline_run_id",
        table_name="document_review_versions",
    )
    op.drop_index(
        "ix_document_review_versions_created_at",
        table_name="document_review_versions",
    )
    op.drop_table("document_review_versions")
    op.drop_index("uq_document_reviews_document_id", table_name="document_reviews")
    op.drop_table("document_reviews")


def _guard_safe_document_review_downgrade(connection: Connection) -> None:
    """Block downgrade once any Review or immutable version exists."""

    review_count = int(connection.scalar(sa.text("select count(*) from document_reviews")) or 0)
    version_count = int(
        connection.scalar(sa.text("select count(*) from document_review_versions")) or 0
    )
    if review_count or version_count:
        raise RuntimeError(
            "Cannot downgrade document Review persistence while Review state exists: "
            f"document_reviews={review_count}, document_review_versions={version_count}.",
        )
