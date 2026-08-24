"""SQLAlchemy table definitions for custom dictionary persistence."""

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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from docmind_api.domain.dictionaries.models import (
    DICTIONARY_DESCRIPTION_MAX_LENGTH,
    DICTIONARY_ENTRY_LABEL_MAX_LENGTH,
    DICTIONARY_FIELD_LABEL_MAX_LENGTH,
    DICTIONARY_ID_MAX_LENGTH,
    DICTIONARY_NAME_MAX_LENGTH,
)
from docmind_api.infrastructure.persistence.metadata import metadata

dictionaries_table = Table(
    "dictionaries",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("external_id", String(length=DICTIONARY_ID_MAX_LENGTH), nullable=False),
    Column("name", String(length=DICTIONARY_NAME_MAX_LENGTH), nullable=False),
    Column("description", String(length=DICTIONARY_DESCRIPTION_MAX_LENGTH), nullable=True),
    Column("status", String(length=32), nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("entries_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("length(trim(external_id)) > 0", name="external_id_not_empty"),
    CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
    CheckConstraint(
        "description is null or length(trim(description)) > 0",
        name="description_not_empty",
    ),
    CheckConstraint("status in ('active', 'inactive')", name="status_supported"),
    CheckConstraint("schema_version > 0", name="schema_version_positive"),
    CheckConstraint("entries_version > 0", name="entries_version_positive"),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    Index("uq_dictionaries_external_id", "external_id", unique=True),
    Index("ix_dictionaries_status", "status"),
)

dictionary_fields_table = Table(
    "dictionary_fields",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column(
        "dictionary_id",
        UUID(as_uuid=True),
        ForeignKey("dictionaries.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("external_id", String(length=DICTIONARY_ID_MAX_LENGTH), nullable=False),
    Column("label", String(length=DICTIONARY_FIELD_LABEL_MAX_LENGTH), nullable=False),
    Column("data_type", String(length=32), nullable=False),
    Column("required", Boolean, nullable=False),
    Column("constraints", JSONB, nullable=False),
    Column("normalization", JSONB, nullable=False),
    Column("format", JSONB, nullable=False),
    Column("is_unique", Boolean, nullable=False),
    Column("sort_order", Integer, nullable=False),
    Column("status", String(length=32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("length(trim(external_id)) > 0", name="external_id_not_empty"),
    CheckConstraint("length(trim(label)) > 0", name="label_not_empty"),
    CheckConstraint(
        "data_type in ('string', 'integer', 'number', 'boolean', 'date', 'datetime')",
        name="data_type_supported",
    ),
    CheckConstraint("jsonb_typeof(constraints) = 'object'", name="constraints_object"),
    CheckConstraint("jsonb_typeof(normalization) = 'object'", name="normalization_object"),
    CheckConstraint("jsonb_typeof(format) = 'object'", name="format_object"),
    CheckConstraint("sort_order >= 0", name="sort_order_non_negative"),
    CheckConstraint("status in ('active', 'inactive')", name="status_supported"),
    CheckConstraint(
        "status = 'active' or required = false",
        name="inactive_fields_not_required",
    ),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    Index(
        "uq_dictionary_fields_dictionary_external_id",
        "dictionary_id",
        "external_id",
        unique=True,
    ),
    Index("ix_dictionary_fields_dictionary_id", "dictionary_id"),
    Index("ix_dictionary_fields_status", "status"),
)

dictionary_entries_table = Table(
    "dictionary_entries",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column(
        "dictionary_id",
        UUID(as_uuid=True),
        ForeignKey("dictionaries.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("external_id", String(length=DICTIONARY_ID_MAX_LENGTH), nullable=False),
    Column("label", String(length=DICTIONARY_ENTRY_LABEL_MAX_LENGTH), nullable=False),
    Column("values", JSONB, nullable=False),
    Column("status", String(length=32), nullable=False),
    Column("sort_order", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("length(trim(external_id)) > 0", name="external_id_not_empty"),
    CheckConstraint("length(trim(label)) > 0", name="label_not_empty"),
    CheckConstraint("jsonb_typeof(values) = 'object'", name="values_object"),
    CheckConstraint("status in ('active', 'inactive')", name="status_supported"),
    CheckConstraint(
        "sort_order is null or sort_order >= 0",
        name="sort_order_non_negative",
    ),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    Index(
        "uq_dictionary_entries_dictionary_external_id",
        "dictionary_id",
        "external_id",
        unique=True,
    ),
    Index("ix_dictionary_entries_dictionary_id", "dictionary_id"),
    Index("ix_dictionary_entries_status", "status"),
    Index("ix_dictionary_entries_label", "label"),
)
