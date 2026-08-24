"""Make catalog external IDs optional.

Revision ID: 20260624_0018
Revises: 20260623_0017
Create Date: 2026-06-24 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260624_0018"
down_revision: str | Sequence[str] | None = "20260623_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow document and attribute catalog external IDs to be omitted."""

    op.drop_constraint(
        op.f("ck_document_types_external_id_snake_case"),
        "document_types",
        type_="check",
    )
    op.alter_column("document_types", "external_id", nullable=True)
    op.create_check_constraint(
        op.f("ck_document_types_external_id_snake_case"),
        "document_types",
        "external_id is null or external_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
    )

    op.drop_constraint(
        op.f("ck_attribute_definitions_external_id_snake_case"),
        "attribute_definitions",
        type_="check",
    )
    op.alter_column("attribute_definitions", "external_id", nullable=True)
    op.create_check_constraint(
        op.f("ck_attribute_definitions_external_id_snake_case"),
        "attribute_definitions",
        "external_id is null or external_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
    )


def downgrade() -> None:
    """Restore required catalog external IDs."""

    op.drop_constraint(
        op.f("ck_attribute_definitions_external_id_snake_case"),
        "attribute_definitions",
        type_="check",
    )
    op.execute(
        "update attribute_definitions "
        "set external_id = 'attribute_definition_' || replace(id::text, '-', '') "
        "where external_id is null",
    )
    op.alter_column("attribute_definitions", "external_id", nullable=False)
    op.create_check_constraint(
        op.f("ck_attribute_definitions_external_id_snake_case"),
        "attribute_definitions",
        "external_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
    )

    op.drop_constraint(
        op.f("ck_document_types_external_id_snake_case"),
        "document_types",
        type_="check",
    )
    op.execute(
        "update document_types "
        "set external_id = 'document_type_' || replace(id::text, '-', '') "
        "where external_id is null",
    )
    op.alter_column("document_types", "external_id", nullable=False)
    op.create_check_constraint(
        op.f("ck_document_types_external_id_snake_case"),
        "document_types",
        "external_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
    )
