"""Create system catalog extensions.

Revision ID: 20260703_0026
Revises: 20260702_0025
Create Date: 2026-07-03 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260703_0026"
down_revision: str | None = "20260702_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BUSINESS_KEY_MAX_LENGTH = 80
LABEL_MAX_LENGTH = 200
TEXT_VALUE_MAX_LENGTH = 2000
SEPARATOR_MAX_LENGTH = 32


def upgrade() -> None:
    """Create generic system catalog definitions and document type extension values."""

    op.create_table(
        "system_catalog_extension_fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("system_catalog_key", sa.String(length=BUSINESS_KEY_MAX_LENGTH), nullable=False),
        sa.Column("code", sa.String(length=BUSINESS_KEY_MAX_LENGTH), nullable=False),
        sa.Column("label", sa.String(length=LABEL_MAX_LENGTH), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False),
        sa.Column("dictionary_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mapped_attribute_definition_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("show_in_overview", sa.Boolean(), nullable=False),
        sa.Column("field_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(system_catalog_key)) > 0",
            name=op.f("ck_system_catalog_extension_fields_system_catalog_key_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(code)) > 0",
            name=op.f("ck_system_catalog_extension_fields_code_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(label)) > 0",
            name=op.f("ck_system_catalog_extension_fields_label_not_empty"),
        ),
        sa.CheckConstraint(
            "value_type in ('dictionary', 'text')",
            name=op.f("ck_system_catalog_extension_fields_value_type_supported"),
        ),
        sa.CheckConstraint(
            "(value_type = 'dictionary' and dictionary_id is not null) or "
            "(value_type = 'text' and dictionary_id is null)",
            name=op.f("ck_system_catalog_extension_fields_value_type_configuration_valid"),
        ),
        sa.CheckConstraint(
            "field_order >= 0",
            name=op.f("ck_system_catalog_extension_fields_field_order_non_negative"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_system_catalog_extension_fields_updated_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(
            ["dictionary_id"],
            ["dictionaries.id"],
            name=op.f("fk_system_catalog_extension_fields_dictionary_id_dictionaries"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["mapped_attribute_definition_id"],
            ["attribute_definitions.id"],
            name=op.f(
                "fk_system_catalog_extension_fields_mapped_attribute_definition_id_"
                "attribute_definitions",
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_catalog_extension_fields")),
    )
    op.create_index(
        "uq_system_catalog_extension_fields_key_code",
        "system_catalog_extension_fields",
        ["system_catalog_key", "code"],
        unique=True,
    )
    op.create_index(
        "ix_system_catalog_extension_fields_key_active",
        "system_catalog_extension_fields",
        ["system_catalog_key", "is_active"],
    )
    op.create_index(
        "ix_system_catalog_extension_fields_dictionary_id",
        "system_catalog_extension_fields",
        ["dictionary_id"],
    )
    op.create_index(
        "ix_sys_catalog_ext_fields_mapped_attr_id",
        "system_catalog_extension_fields",
        ["mapped_attribute_definition_id"],
    )

    op.create_table(
        "document_type_extension_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extension_field_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dictionary_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("text_value", sa.String(length=TEXT_VALUE_MAX_LENGTH), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "text_value is null or length(trim(text_value)) > 0",
            name=op.f("ck_document_type_extension_values_text_not_empty"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_document_type_extension_values_updated_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(
            ["dictionary_entry_id"],
            ["dictionary_entries.id"],
            name=op.f("fk_document_type_extension_values_dictionary_entry_id_dictionary_entries"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_type_id"],
            ["document_types.id"],
            name=op.f("fk_document_type_extension_values_document_type_id_document_types"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["extension_field_id"],
            ["system_catalog_extension_fields.id"],
            name=op.f(
                "fk_document_type_extension_values_extension_field_id_"
                "system_catalog_extension_fields",
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_type_extension_values")),
    )
    op.create_index(
        "uq_document_type_extension_values_type_field",
        "document_type_extension_values",
        ["document_type_id", "extension_field_id"],
        unique=True,
    )
    op.create_index(
        "ix_document_type_extension_values_document_type_id",
        "document_type_extension_values",
        ["document_type_id"],
    )
    op.create_index(
        "ix_document_type_extension_values_extension_field_id",
        "document_type_extension_values",
        ["extension_field_id"],
    )
    op.create_index(
        "ix_document_type_extension_values_dictionary_entry_id",
        "document_type_extension_values",
        ["dictionary_entry_id"],
    )

    op.create_table(
        "system_catalog_display_modes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("system_catalog_key", sa.String(length=BUSINESS_KEY_MAX_LENGTH), nullable=False),
        sa.Column("name", sa.String(length=LABEL_MAX_LENGTH), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(system_catalog_key)) > 0",
            name=op.f("ck_system_catalog_display_modes_system_catalog_key_not_empty"),
        ),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name=op.f("ck_system_catalog_display_modes_name_not_empty"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_system_catalog_display_modes_updated_at_not_before_created_at"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_catalog_display_modes")),
    )
    op.create_index(
        "ix_system_catalog_display_modes_key_active",
        "system_catalog_display_modes",
        ["system_catalog_key", "is_active"],
    )
    op.create_index(
        "uq_system_catalog_display_modes_key_name",
        "system_catalog_display_modes",
        ["system_catalog_key", "name"],
        unique=True,
    )
    op.create_index(
        "uq_system_catalog_display_modes_default",
        "system_catalog_display_modes",
        ["system_catalog_key"],
        unique=True,
        postgresql_where=sa.text("is_default and is_active"),
    )

    op.create_table(
        "system_catalog_display_mode_parts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_mode_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("part_order", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("extension_field_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("separator_before", sa.String(length=SEPARATOR_MAX_LENGTH), nullable=True),
        sa.CheckConstraint(
            "part_order >= 0",
            name=op.f("ck_system_catalog_display_mode_parts_part_order_non_negative"),
        ),
        sa.CheckConstraint(
            "source_type in ('base_name', 'extension_field')",
            name=op.f("ck_system_catalog_display_mode_parts_source_type_supported"),
        ),
        sa.CheckConstraint(
            "(source_type = 'base_name' and extension_field_id is null) or "
            "(source_type = 'extension_field' and extension_field_id is not null)",
            name=op.f("ck_system_catalog_display_mode_parts_source_configuration_valid"),
        ),
        sa.CheckConstraint(
            "separator_before is null or length(separator_before) > 0",
            name=op.f("ck_system_catalog_display_mode_parts_separator_before_not_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["display_mode_id"],
            ["system_catalog_display_modes.id"],
            name=op.f(
                "fk_system_catalog_display_mode_parts_display_mode_id_system_catalog_display_modes",
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["extension_field_id"],
            ["system_catalog_extension_fields.id"],
            name=op.f(
                "fk_system_catalog_display_mode_parts_extension_field_id_"
                "system_catalog_extension_fields",
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_catalog_display_mode_parts")),
    )
    op.create_index(
        "uq_system_catalog_display_mode_parts_mode_order",
        "system_catalog_display_mode_parts",
        ["display_mode_id", "part_order"],
        unique=True,
    )
    op.create_index(
        "ix_system_catalog_display_mode_parts_display_mode_id",
        "system_catalog_display_mode_parts",
        ["display_mode_id"],
    )
    op.create_index(
        "ix_system_catalog_display_mode_parts_extension_field_id",
        "system_catalog_display_mode_parts",
        ["extension_field_id"],
    )


def downgrade() -> None:
    """Remove system catalog extension persistence after an empty-state guard."""

    _guard_safe_system_catalog_extensions_downgrade(op.get_bind())

    op.drop_table("system_catalog_display_mode_parts")
    op.drop_table("system_catalog_display_modes")
    op.drop_table("document_type_extension_values")
    op.drop_table("system_catalog_extension_fields")


def _guard_safe_system_catalog_extensions_downgrade(connection: Connection) -> None:
    """Block downgrade once system catalog configuration or values exist."""

    unsafe_tables: list[str] = []
    for table_name in (
        "document_type_extension_values",
        "system_catalog_display_mode_parts",
        "system_catalog_display_modes",
        "system_catalog_extension_fields",
    ):
        row_count = int(connection.scalar(sa.text(f"select count(*) from {table_name}")) or 0)
        if row_count:
            unsafe_tables.append(f"{table_name}={row_count}")

    if unsafe_tables:
        raise RuntimeError(
            "Cannot downgrade system catalog extensions while configuration or value state "
            f"exists: {', '.join(unsafe_tables)}.",
        )
