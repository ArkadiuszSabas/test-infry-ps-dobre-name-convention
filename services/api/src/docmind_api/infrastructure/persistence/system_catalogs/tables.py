"""SQLAlchemy table definitions for system catalog extensions."""

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
from sqlalchemy.dialects.postgresql import UUID

from docmind_api.domain.system_catalogs.models import (
    SYSTEM_CATALOG_CODE_MAX_LENGTH,
    SYSTEM_CATALOG_KEY_MAX_LENGTH,
    SYSTEM_CATALOG_LABEL_MAX_LENGTH,
    SYSTEM_CATALOG_SEPARATOR_MAX_LENGTH,
    SYSTEM_CATALOG_TEXT_VALUE_MAX_LENGTH,
)
from docmind_api.infrastructure.persistence.metadata import metadata

system_catalog_extension_fields_table = Table(
    "system_catalog_extension_fields",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("system_catalog_key", String(length=SYSTEM_CATALOG_KEY_MAX_LENGTH), nullable=False),
    Column("code", String(length=SYSTEM_CATALOG_CODE_MAX_LENGTH), nullable=False),
    Column("label", String(length=SYSTEM_CATALOG_LABEL_MAX_LENGTH), nullable=False),
    Column("value_type", String(length=32), nullable=False),
    Column(
        "dictionary_id",
        UUID(as_uuid=True),
        ForeignKey("dictionaries.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column(
        "mapped_attribute_definition_id",
        UUID(as_uuid=True),
        ForeignKey("attribute_definitions.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("is_required", Boolean, nullable=False),
    Column("show_in_overview", Boolean, nullable=False),
    Column("field_order", Integer, nullable=False),
    Column("is_active", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("length(trim(system_catalog_key)) > 0", name="system_catalog_key_not_empty"),
    CheckConstraint("length(trim(code)) > 0", name="code_not_empty"),
    CheckConstraint("length(trim(label)) > 0", name="label_not_empty"),
    CheckConstraint("value_type in ('dictionary', 'text')", name="value_type_supported"),
    CheckConstraint(
        "(value_type = 'dictionary' and dictionary_id is not null) or "
        "(value_type = 'text' and dictionary_id is null)",
        name="value_type_configuration_valid",
    ),
    CheckConstraint("field_order >= 0", name="field_order_non_negative"),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    Index(
        "uq_system_catalog_extension_fields_key_code",
        "system_catalog_key",
        "code",
        unique=True,
    ),
    Index(
        "ix_system_catalog_extension_fields_key_active",
        "system_catalog_key",
        "is_active",
    ),
    Index(
        "ix_system_catalog_extension_fields_dictionary_id",
        "dictionary_id",
    ),
    Index(
        "ix_sys_catalog_ext_fields_mapped_attr_id",
        "mapped_attribute_definition_id",
    ),
)

document_type_extension_values_table = Table(
    "document_type_extension_values",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column(
        "document_type_id",
        UUID(as_uuid=True),
        ForeignKey("document_types.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "extension_field_id",
        UUID(as_uuid=True),
        ForeignKey("system_catalog_extension_fields.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "dictionary_entry_id",
        UUID(as_uuid=True),
        ForeignKey("dictionary_entries.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("text_value", String(length=SYSTEM_CATALOG_TEXT_VALUE_MAX_LENGTH), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("text_value is null or length(trim(text_value)) > 0", name="text_not_empty"),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    Index(
        "uq_document_type_extension_values_type_field",
        "document_type_id",
        "extension_field_id",
        unique=True,
    ),
    Index("ix_document_type_extension_values_document_type_id", "document_type_id"),
    Index("ix_document_type_extension_values_extension_field_id", "extension_field_id"),
    Index("ix_document_type_extension_values_dictionary_entry_id", "dictionary_entry_id"),
)

system_catalog_display_modes_table = Table(
    "system_catalog_display_modes",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("system_catalog_key", String(length=SYSTEM_CATALOG_KEY_MAX_LENGTH), nullable=False),
    Column("name", String(length=SYSTEM_CATALOG_LABEL_MAX_LENGTH), nullable=False),
    Column("is_default", Boolean, nullable=False),
    Column("is_active", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("length(trim(system_catalog_key)) > 0", name="system_catalog_key_not_empty"),
    CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    Index("ix_system_catalog_display_modes_key_active", "system_catalog_key", "is_active"),
    Index(
        "uq_system_catalog_display_modes_key_name",
        "system_catalog_key",
        "name",
        unique=True,
    ),
    Index(
        "uq_system_catalog_display_modes_default",
        "system_catalog_key",
        unique=True,
        postgresql_where=text("is_default and is_active"),
    ),
)

system_catalog_display_mode_parts_table = Table(
    "system_catalog_display_mode_parts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column(
        "display_mode_id",
        UUID(as_uuid=True),
        ForeignKey("system_catalog_display_modes.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("part_order", Integer, nullable=False),
    Column("source_type", String(length=32), nullable=False),
    Column(
        "extension_field_id",
        UUID(as_uuid=True),
        ForeignKey("system_catalog_extension_fields.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("separator_before", String(length=SYSTEM_CATALOG_SEPARATOR_MAX_LENGTH), nullable=True),
    CheckConstraint("part_order >= 0", name="part_order_non_negative"),
    CheckConstraint(
        "source_type in ('base_name', 'extension_field')", name="source_type_supported"
    ),
    CheckConstraint(
        "(source_type = 'base_name' and extension_field_id is null) or "
        "(source_type = 'extension_field' and extension_field_id is not null)",
        name="source_configuration_valid",
    ),
    CheckConstraint(
        "separator_before is null or length(separator_before) > 0",
        name="separator_before_not_empty",
    ),
    Index(
        "uq_system_catalog_display_mode_parts_mode_order",
        "display_mode_id",
        "part_order",
        unique=True,
    ),
    Index("ix_system_catalog_display_mode_parts_display_mode_id", "display_mode_id"),
    Index("ix_system_catalog_display_mode_parts_extension_field_id", "extension_field_id"),
)
