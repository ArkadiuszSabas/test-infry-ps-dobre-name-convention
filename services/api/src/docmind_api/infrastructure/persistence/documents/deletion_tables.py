"""SQLAlchemy table for payload-free permanent-deletion tombstones."""

from sqlalchemy import CheckConstraint, Column, DateTime, String, Table, exists, select
from sqlalchemy.dialects.postgresql import UUID

from docmind_api.infrastructure.persistence.metadata import metadata

document_deletion_operations_table = Table(
    "document_deletion_operations",
    metadata,
    Column("document_id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("operation_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column("stage", String(length=32), nullable=False),
    Column("connector_instance_id", String(length=200), nullable=True),
    Column("policy", String(length=32), nullable=True),
    Column("warning_code", String(length=100), nullable=True),
    Column("failure_stage", String(length=32), nullable=True),
    Column("error_code", String(length=100), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    CheckConstraint(
        "stage in ('requested', 'connector_prepared', 'content_deleted', 'completed')",
        name="stage_supported",
    ),
    CheckConstraint(
        "policy is null or policy in ('not_applicable', 'preserve', 'delete', 'block')",
        name="policy_supported",
    ),
    CheckConstraint(
        "failure_stage is null or failure_stage in ('connector', 'content', 'database')",
        name="failure_stage_supported",
    ),
    CheckConstraint(
        "(failure_stage is null and error_code is null) "
        "or (failure_stage is not null and error_code is not null)",
        name="failure_fields_complete",
    ),
    CheckConstraint(
        "(stage = 'completed' and completed_at is not null) "
        "or (stage <> 'completed' and completed_at is null)",
        name="completed_at_matches_stage",
    ),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
)


def document_is_not_deleting(document_id: object):
    """Return a reusable SQL predicate that hides actively deleting documents."""

    return ~exists(
        select(document_deletion_operations_table.c.document_id).where(
            document_deletion_operations_table.c.document_id == document_id,
            document_deletion_operations_table.c.stage != "completed",
        )
    )
