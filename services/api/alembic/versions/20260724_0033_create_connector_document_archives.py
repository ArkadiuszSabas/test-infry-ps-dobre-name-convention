"""Create durable connector approved-document archive state.

Revision ID: 20260724_0033
Revises: 20260727_0032
Create Date: 2026-07-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260724_0033"
down_revision = "20260727_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_document_archives",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_instance_id", sa.String(length=200), nullable=False),
        sa.Column("handler_id", sa.String(length=160), nullable=False),
        sa.Column("review_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("folder_path", sa.String(length=1024), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("drive_item_id", sa.String(length=512), nullable=True),
        sa.Column("web_url", sa.String(length=2048), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("failure_stage", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(connector_instance_id)) > 0",
            name=op.f("ck_connector_document_archives_instance_id_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(handler_id)) > 0",
            name=op.f("ck_connector_document_archives_handler_id_not_empty"),
        ),
        sa.CheckConstraint(
            "review_version > 0",
            name=op.f("ck_connector_document_archives_review_version_positive"),
        ),
        sa.CheckConstraint(
            "status in ('pending', 'succeeded', 'failed')",
            name=op.f("ck_connector_document_archives_status_supported"),
        ),
        sa.CheckConstraint(
            "length(trim(folder_path)) > 0",
            name=op.f("ck_connector_document_archives_folder_path_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(file_name)) > 0",
            name=op.f("ck_connector_document_archives_file_name_not_empty"),
        ),
        sa.CheckConstraint(
            "(status = 'pending' and drive_item_id is null and web_url is null "
            "and error_code is null and failure_stage is null) "
            "or (status = 'succeeded' and drive_item_id is not null and web_url is not null "
            "and error_code is null and failure_stage is null) "
            "or (status = 'failed' and drive_item_id is null and web_url is null "
            "and error_code is not null and failure_stage in ('preflight', 'io'))",
            name=op.f("ck_connector_document_archives_terminal_fields_match_status"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_connector_document_archives_updated_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="RESTRICT",
            name=op.f("fk_connector_document_archives_document_id_documents"),
        ),
        sa.PrimaryKeyConstraint(
            "document_id",
            name=op.f("pk_connector_document_archives"),
        ),
    )


def downgrade() -> None:
    archive_count = op.get_bind().scalar(
        sa.text("select count(*) from connector_document_archives")
    )
    if archive_count:
        raise RuntimeError(
            "Cannot downgrade connector document archives while archive state exists."
        )
    op.drop_table("connector_document_archives")
