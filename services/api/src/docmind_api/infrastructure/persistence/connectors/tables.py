"""SQLAlchemy tables for API-owned connector configuration."""

from sqlalchemy import CheckConstraint, Column, DateTime, String, Table
from sqlalchemy.dialects.postgresql import JSONB

from docmind_api.infrastructure.persistence.metadata import metadata

connector_instance_configurations_table = Table(
    "connector_instance_configurations",
    metadata,
    Column("connector_instance_id", String(length=160), primary_key=True, nullable=False),
    Column("values", JSONB, nullable=False),
    Column("api_key_salt", String(length=64), nullable=True),
    Column("api_key_hash", String(length=64), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("length(trim(connector_instance_id)) > 0", name="instance_id_not_empty"),
    CheckConstraint("jsonb_typeof(values) = 'object'", name="values_object"),
    CheckConstraint(
        "(api_key_salt is null and api_key_hash is null) "
        "or (api_key_salt is not null and api_key_hash is not null)",
        name="api_key_complete",
    ),
    CheckConstraint("created_at <= updated_at", name="updated_at_not_before_created_at"),
)
