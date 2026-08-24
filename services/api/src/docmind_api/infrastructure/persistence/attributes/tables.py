"""SQLAlchemy table definitions for attribute catalog persistence."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from docmind_api.domain.attributes.models import (
    ATTRIBUTE_ALLOWED_VALUE_MAX_LENGTH,
    ATTRIBUTE_CATEGORY_MAX_LENGTH,
    ATTRIBUTE_COMMENT_MAX_LENGTH,
    ATTRIBUTE_ID_MAX_LENGTH,
    ATTRIBUTE_NAME_MAX_LENGTH,
)
from docmind_api.infrastructure.persistence.metadata import metadata

attribute_categories_table = Table(
    "attribute_categories",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("external_id", String(length=ATTRIBUTE_ID_MAX_LENGTH), nullable=False),
    Column("label", String(length=ATTRIBUTE_CATEGORY_MAX_LENGTH), nullable=False),
    Column("flags", JSONB, nullable=False),
    Column("status", String(length=32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("length(trim(external_id)) > 0", name="external_id_not_empty"),
    CheckConstraint("length(trim(label)) > 0", name="label_not_empty"),
    CheckConstraint("jsonb_typeof(flags) = 'object'", name="flags_object"),
    CheckConstraint("status in ('active', 'inactive')", name="status_supported"),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
    Index("uq_attribute_categories_external_id", "external_id", unique=True),
    Index("ix_attribute_categories_status", "status"),
)

attribute_definitions_table = Table(
    "attribute_definitions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("external_id", String(length=ATTRIBUTE_ID_MAX_LENGTH), nullable=True),
    Column("name", String(length=ATTRIBUTE_NAME_MAX_LENGTH), nullable=False),
    Column(
        "category_id",
        UUID(as_uuid=True),
        ForeignKey("attribute_categories.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("data_type", String(length=32), nullable=False),
    Column("constraints", JSONB, nullable=False),
    Column("allowed_values", JSONB, nullable=False),
    Column("value_source", String(length=32), nullable=False),
    Column(
        "dictionary_id",
        UUID(as_uuid=True),
        ForeignKey("dictionaries.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("source", String(length=32), nullable=False),
    Column("comment", String(length=ATTRIBUTE_COMMENT_MAX_LENGTH), nullable=True),
    Column("llm_context", Text, nullable=True),
    Column("status", String(length=32), nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "external_id is null or length(trim(external_id)) > 0",
        name="external_id_not_empty",
    ),
    CheckConstraint(
        "length(trim(name)) > 0",
        name="name_not_empty",
    ),
    CheckConstraint(
        "data_type in ("
        "'legacy_scalar', 'string', 'integer', 'number', 'boolean', 'date', 'datetime'"
        ")",
        name="data_type_supported",
    ),
    CheckConstraint(
        "jsonb_typeof(constraints) = 'object'",
        name="constraints_object",
    ),
    CheckConstraint(
        "jsonb_typeof(allowed_values) = 'array'",
        name="allowed_values_array",
    ),
    CheckConstraint(
        f"jsonb_text_array_is_valid(allowed_values, {ATTRIBUTE_ALLOWED_VALUE_MAX_LENGTH})",
        name="allowed_values_entries_valid",
    ),
    CheckConstraint(
        "data_type in ('legacy_scalar', 'string') or jsonb_array_length(allowed_values) = 0",
        name="allowed_values_match_data_type",
    ),
    CheckConstraint(
        "value_source in ('free_text', 'inline_allowed_values', 'dictionary')",
        name="value_source_supported",
    ),
    CheckConstraint(
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
        name="value_source_configuration_valid",
    ),
    CheckConstraint(
        "source in ('ai', 'user')",
        name="source_supported",
    ),
    CheckConstraint(
        "comment is null or length(trim(comment)) > 0",
        name="comment_not_empty",
    ),
    CheckConstraint(
        "llm_context is null or length(trim(llm_context)) > 0",
        name="llm_context_not_empty",
    ),
    CheckConstraint(
        "status in ('active', 'inactive')",
        name="status_supported",
    ),
    CheckConstraint(
        "schema_version > 0",
        name="schema_version_positive",
    ),
    CheckConstraint(
        "created_at <= updated_at",
        name="updated_at_not_before_created_at",
    ),
    Index("ix_attribute_definitions_category_id", "category_id"),
    Index("ix_attribute_definitions_dictionary_id", "dictionary_id"),
    Index("ix_attribute_definitions_status", "status"),
    Index("uq_attribute_definitions_external_id", "external_id", unique=True),
)
