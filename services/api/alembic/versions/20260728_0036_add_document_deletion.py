"""Add permanent document deletion fence and dedicated role.

Revision ID: 20260728_0036
Revises: 20260728_0035
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0036"
down_revision: str | Sequence[str] | None = "20260728_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_role_assignments_role_supported"),
        "role_assignments",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_role_assignments_role_supported"),
        "role_assignments",
        "role in ('admin', 'reviewer', 'operator', 'viewer', 'document_deleter')",
    )

    op.create_table(
        "document_deletion_operations",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("operation_id", sa.UUID(), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("connector_instance_id", sa.String(length=200), nullable=True),
        sa.Column("policy", sa.String(length=32), nullable=True),
        sa.Column("warning_code", sa.String(length=100), nullable=True),
        sa.Column("failure_stage", sa.String(length=32), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "stage in ('requested', 'connector_prepared', 'content_deleted', 'completed')",
            name=op.f("ck_document_deletion_operations_stage_supported"),
        ),
        sa.CheckConstraint(
            "policy is null or policy in ('not_applicable', 'preserve', 'delete', 'block')",
            name=op.f("ck_document_deletion_operations_policy_supported"),
        ),
        sa.CheckConstraint(
            "failure_stage is null or failure_stage in ('connector', 'content', 'database')",
            name=op.f("ck_document_deletion_operations_failure_stage_supported"),
        ),
        sa.CheckConstraint(
            "(failure_stage is null and error_code is null) "
            "or (failure_stage is not null and error_code is not null)",
            name=op.f("ck_document_deletion_operations_failure_fields_complete"),
        ),
        sa.CheckConstraint(
            "(stage = 'completed' and completed_at is not null) "
            "or (stage <> 'completed' and completed_at is null)",
            name=op.f("ck_document_deletion_operations_completed_at_matches_stage"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_document_deletion_operations_updated_at_not_before_created_at"),
        ),
        sa.PrimaryKeyConstraint(
            "document_id",
            name=op.f("pk_document_deletion_operations"),
        ),
        sa.UniqueConstraint(
            "operation_id",
            name=op.f("uq_document_deletion_operations_operation_id"),
        ),
    )

    op.drop_constraint(
        op.f("ck_connector_document_archives_status_supported"),
        "connector_document_archives",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_connector_document_archives_terminal_fields_match_status"),
        "connector_document_archives",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_connector_document_archives_status_supported"),
        "connector_document_archives",
        "status in ('pending', 'succeeded', 'failed', 'cancelled')",
    )
    op.create_check_constraint(
        op.f("ck_connector_document_archives_terminal_fields_match_status"),
        "connector_document_archives",
        "(status = 'pending' and drive_item_id is null and web_url is null "
        "and error_code is null and failure_stage is null) "
        "or (status = 'succeeded' and drive_item_id is not null and web_url is not null "
        "and error_code is null and failure_stage is null) "
        "or (status = 'failed' and drive_item_id is null and web_url is null "
        "and error_code is not null and failure_stage in ('preflight', 'io')) "
        "or (status = 'cancelled' and drive_item_id is null and web_url is null "
        "and error_code is not null and failure_stage is null)",
    )
    _create_deletion_fence_triggers()


def downgrade() -> None:
    connection = op.get_bind()
    deletion_count = connection.execute(
        sa.text("select count(*) from document_deletion_operations")
    ).scalar_one()
    deleter_count = connection.execute(
        sa.text("select count(*) from role_assignments where role = 'document_deleter'")
    ).scalar_one()
    cancelled_archive_count = connection.execute(
        sa.text("select count(*) from connector_document_archives where status = 'cancelled'")
    ).scalar_one()
    if deletion_count or deleter_count or cancelled_archive_count:
        raise RuntimeError(
            "Cannot downgrade document deletion while deletion tombstones, document-deleter "
            "assignments, or cancelled connector archives exist."
        )

    _drop_deletion_fence_triggers()
    op.drop_constraint(
        op.f("ck_connector_document_archives_terminal_fields_match_status"),
        "connector_document_archives",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_connector_document_archives_status_supported"),
        "connector_document_archives",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_connector_document_archives_status_supported"),
        "connector_document_archives",
        "status in ('pending', 'succeeded', 'failed')",
    )
    op.create_check_constraint(
        op.f("ck_connector_document_archives_terminal_fields_match_status"),
        "connector_document_archives",
        "(status = 'pending' and drive_item_id is null and web_url is null "
        "and error_code is null and failure_stage is null) "
        "or (status = 'succeeded' and drive_item_id is not null and web_url is not null "
        "and error_code is null and failure_stage is null) "
        "or (status = 'failed' and drive_item_id is null and web_url is null "
        "and error_code is not null and failure_stage in ('preflight', 'io'))",
    )
    op.drop_table("document_deletion_operations")
    op.drop_constraint(
        op.f("ck_role_assignments_role_supported"),
        "role_assignments",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_role_assignments_role_supported"),
        "role_assignments",
        "role in ('admin', 'reviewer', 'operator', 'viewer')",
    )


def _create_deletion_fence_triggers() -> None:
    op.execute(
        """
        create function reject_document_write_while_deleting()
        returns trigger
        language plpgsql
        as $$
        begin
            if exists (
                select 1
                from document_deletion_operations
                where document_id = new.document_id
                  and stage <> 'completed'
            ) then
                raise exception 'DOCUMENT_DELETE_IN_PROGRESS'
                    using errcode = '23514';
            end if;
            return new;
        end;
        $$;
        """
    )
    op.execute(
        """
        create function reject_review_version_write_while_deleting()
        returns trigger
        language plpgsql
        as $$
        begin
            if exists (
                select 1
                from document_reviews review
                join document_deletion_operations deletion
                  on deletion.document_id = review.document_id
                where review.id = new.review_id
                  and deletion.stage <> 'completed'
            ) then
                raise exception 'DOCUMENT_DELETE_IN_PROGRESS'
                    using errcode = '23514';
            end if;
            return new;
        end;
        $$;
        """
    )
    for table in (
        "ocr_pipeline_runs",
        "document_reviews",
        "document_approval_workflows",
        "document_approval_decisions",
        "document_type_change_audit_events",
    ):
        op.execute(
            f"""
            create trigger trg_{table}_deletion_fence
            before insert or update on {table}
            for each row execute function reject_document_write_while_deleting();
            """
        )
    op.execute(
        """
        create trigger trg_document_review_versions_deletion_fence
        before insert or update on document_review_versions
        for each row execute function reject_review_version_write_while_deleting();
        """
    )
    op.execute(
        """
        create trigger trg_connector_document_archives_deletion_fence
        before insert on connector_document_archives
        for each row execute function reject_document_write_while_deleting();
        """
    )


def _drop_deletion_fence_triggers() -> None:
    for table in (
        "ocr_pipeline_runs",
        "document_reviews",
        "document_approval_workflows",
        "document_approval_decisions",
        "document_type_change_audit_events",
        "document_review_versions",
        "connector_document_archives",
    ):
        op.execute(f"drop trigger if exists trg_{table}_deletion_fence on {table}")
    op.execute("drop function if exists reject_review_version_write_while_deleting()")
    op.execute("drop function if exists reject_document_write_while_deleting()")
