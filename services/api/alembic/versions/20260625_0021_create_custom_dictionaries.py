"""Create custom dictionaries.

Revision ID: 20260625_0021
Revises: 20260624_0020
Create Date: 2026-06-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260625_0021"
down_revision: str | None = "20260624_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BUSINESS_ID_MAX_LENGTH = 80
DESCRIPTION_MAX_LENGTH = 2000
LABEL_MAX_LENGTH = 200
NAME_MAX_LENGTH = 200


def upgrade() -> None:
    """Create dictionary tables and bind attributes to dictionary value sources."""

    op.create_table(
        "dictionaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=BUSINESS_ID_MAX_LENGTH), nullable=False),
        sa.Column("name", sa.String(length=NAME_MAX_LENGTH), nullable=False),
        sa.Column("description", sa.String(length=DESCRIPTION_MAX_LENGTH), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("entries_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(external_id)) > 0",
            name=op.f("ck_dictionaries_external_id_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name=op.f("ck_dictionaries_name_not_empty"),
        ),
        sa.CheckConstraint(
            "description is null or length(trim(description)) > 0",
            name=op.f("ck_dictionaries_description_not_empty"),
        ),
        sa.CheckConstraint(
            "status in ('active', 'inactive')",
            name=op.f("ck_dictionaries_status_supported"),
        ),
        sa.CheckConstraint(
            "schema_version > 0",
            name=op.f("ck_dictionaries_schema_version_positive"),
        ),
        sa.CheckConstraint(
            "entries_version > 0",
            name=op.f("ck_dictionaries_entries_version_positive"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_dictionaries_updated_at_not_before_created_at"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dictionaries")),
    )
    op.create_index("ix_dictionaries_status", "dictionaries", ["status"])
    op.create_index(
        "uq_dictionaries_external_id",
        "dictionaries",
        ["external_id"],
        unique=True,
    )

    op.create_table(
        "dictionary_fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dictionary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=BUSINESS_ID_MAX_LENGTH), nullable=False),
        sa.Column("label", sa.String(length=LABEL_MAX_LENGTH), nullable=False),
        sa.Column("data_type", sa.String(length=32), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalization", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("format", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_unique", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(external_id)) > 0",
            name=op.f("ck_dictionary_fields_external_id_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(label)) > 0",
            name=op.f("ck_dictionary_fields_label_not_empty"),
        ),
        sa.CheckConstraint(
            "data_type in ('string', 'integer', 'number', 'boolean', 'date', 'datetime')",
            name=op.f("ck_dictionary_fields_data_type_supported"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(constraints) = 'object'",
            name=op.f("ck_dictionary_fields_constraints_object"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(normalization) = 'object'",
            name=op.f("ck_dictionary_fields_normalization_object"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(format) = 'object'",
            name=op.f("ck_dictionary_fields_format_object"),
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name=op.f("ck_dictionary_fields_sort_order_non_negative"),
        ),
        sa.CheckConstraint(
            "status in ('active', 'inactive')",
            name=op.f("ck_dictionary_fields_status_supported"),
        ),
        sa.CheckConstraint(
            "status = 'active' or required = false",
            name=op.f("ck_dictionary_fields_inactive_fields_not_required"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_dictionary_fields_updated_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(
            ["dictionary_id"],
            ["dictionaries.id"],
            name=op.f("fk_dictionary_fields_dictionary_id_dictionaries"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dictionary_fields")),
    )
    op.create_index(
        "ix_dictionary_fields_dictionary_id",
        "dictionary_fields",
        ["dictionary_id"],
    )
    op.create_index("ix_dictionary_fields_status", "dictionary_fields", ["status"])
    op.create_index(
        "uq_dictionary_fields_dictionary_external_id",
        "dictionary_fields",
        ["dictionary_id", "external_id"],
        unique=True,
    )

    op.create_table(
        "dictionary_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dictionary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=BUSINESS_ID_MAX_LENGTH), nullable=False),
        sa.Column("label", sa.String(length=LABEL_MAX_LENGTH), nullable=False),
        sa.Column("values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(external_id)) > 0",
            name=op.f("ck_dictionary_entries_external_id_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(label)) > 0",
            name=op.f("ck_dictionary_entries_label_not_empty"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(values) = 'object'",
            name=op.f("ck_dictionary_entries_values_object"),
        ),
        sa.CheckConstraint(
            "status in ('active', 'inactive')",
            name=op.f("ck_dictionary_entries_status_supported"),
        ),
        sa.CheckConstraint(
            "sort_order is null or sort_order >= 0",
            name=op.f("ck_dictionary_entries_sort_order_non_negative"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_dictionary_entries_updated_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(
            ["dictionary_id"],
            ["dictionaries.id"],
            name=op.f("fk_dictionary_entries_dictionary_id_dictionaries"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dictionary_entries")),
    )
    op.create_index(
        "ix_dictionary_entries_dictionary_id",
        "dictionary_entries",
        ["dictionary_id"],
    )
    op.create_index("ix_dictionary_entries_label", "dictionary_entries", ["label"])
    op.create_index("ix_dictionary_entries_status", "dictionary_entries", ["status"])
    op.create_index(
        "uq_dictionary_entries_dictionary_external_id",
        "dictionary_entries",
        ["dictionary_id", "external_id"],
        unique=True,
    )

    op.add_column(
        "attribute_definitions",
        sa.Column(
            "value_source",
            sa.String(length=32),
            nullable=False,
            server_default="free_text",
        ),
    )
    op.add_column(
        "attribute_definitions",
        sa.Column("dictionary_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        update attribute_definitions
        set value_source = 'inline_allowed_values'
        where jsonb_array_length(allowed_values) > 0
        """,
    )
    op.alter_column("attribute_definitions", "value_source", server_default=None)
    op.create_foreign_key(
        op.f("fk_attribute_definitions_dictionary_id_dictionaries"),
        "attribute_definitions",
        "dictionaries",
        ["dictionary_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_attribute_definitions_dictionary_id",
        "attribute_definitions",
        ["dictionary_id"],
    )
    op.create_check_constraint(
        op.f("ck_attribute_definitions_value_source_supported"),
        "attribute_definitions",
        "value_source in ('free_text', 'inline_allowed_values', 'dictionary')",
    )
    op.create_check_constraint(
        op.f("ck_attribute_definitions_value_source_configuration_valid"),
        "attribute_definitions",
        "("
        "value_source = 'free_text' and jsonb_array_length(allowed_values) = 0 "
        "and dictionary_id is null"
        ") or ("
        "value_source = 'inline_allowed_values' and jsonb_array_length(allowed_values) > 0 "
        "and dictionary_id is null"
        ") or ("
        "value_source = 'dictionary' and jsonb_array_length(allowed_values) = 0 "
        "and dictionary_id is not null and data_type = 'string'"
        ")",
    )


def downgrade() -> None:
    """Remove custom dictionary state and attribute dictionary bindings."""

    _guard_safe_custom_dictionary_downgrade(op.get_bind())

    op.drop_constraint(
        op.f("ck_attribute_definitions_value_source_configuration_valid"),
        "attribute_definitions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_attribute_definitions_value_source_supported"),
        "attribute_definitions",
        type_="check",
    )
    op.drop_index("ix_attribute_definitions_dictionary_id", table_name="attribute_definitions")
    op.drop_constraint(
        op.f("fk_attribute_definitions_dictionary_id_dictionaries"),
        "attribute_definitions",
        type_="foreignkey",
    )
    op.drop_column("attribute_definitions", "dictionary_id")
    op.drop_column("attribute_definitions", "value_source")

    op.drop_table("dictionary_entries")
    op.drop_table("dictionary_fields")
    op.drop_table("dictionaries")


def _guard_safe_custom_dictionary_downgrade(connection: Connection) -> None:
    """Block downgrade once custom dictionary or binding data exists."""

    unsafe_tables: list[str] = []
    for table_name in ("dictionary_entries", "dictionary_fields", "dictionaries"):
        row_count = int(connection.scalar(sa.text(f"select count(*) from {table_name}")) or 0)
        if row_count:
            unsafe_tables.append(f"{table_name}={row_count}")

    unsafe_attribute_rows = int(
        connection.scalar(
            sa.text(
                """
                select count(*)
                from attribute_definitions
                where value_source <> 'free_text'
                   or dictionary_id is not null
                """,
            ),
        )
        or 0,
    )
    if unsafe_attribute_rows:
        unsafe_tables.append(f"attribute_definitions={unsafe_attribute_rows}")

    if unsafe_tables:
        raise RuntimeError(
            "Cannot downgrade custom dictionaries while dictionary or dictionary-bound "
            f"attribute state exists: {', '.join(unsafe_tables)}.",
        )
