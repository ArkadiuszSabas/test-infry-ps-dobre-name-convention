"""Alembic environment for API-owned PostgreSQL schema."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection

from docmind_api.infrastructure.persistence.attribute_requirements import (
    tables as attribute_requirement_tables,
)
from docmind_api.infrastructure.persistence.attributes import tables as attribute_tables
from docmind_api.infrastructure.persistence.auth import tables as auth_tables
from docmind_api.infrastructure.persistence.connectors import (
    document_archive_tables as connector_document_archive_tables,
)
from docmind_api.infrastructure.persistence.dictionaries import tables as dictionary_tables
from docmind_api.infrastructure.persistence.document_review import tables as document_review_tables
from docmind_api.infrastructure.persistence.document_types import tables as document_type_tables
from docmind_api.infrastructure.persistence.documents import (
    deletion_tables as document_deletion_tables,
)
from docmind_api.infrastructure.persistence.documents import tables as document_tables
from docmind_api.infrastructure.persistence.ocr_pipeline_runs import (
    tables as ocr_pipeline_run_tables,
)
from docmind_api.infrastructure.persistence.ocr_pipelines import tables as ocr_pipeline_tables
from docmind_api.infrastructure.persistence.runtime_permissions import (
    apply_runtime_database_permissions,
)
from docmind_api.infrastructure.persistence.sql import create_database_engine
from docmind_api.infrastructure.persistence.system_catalogs import tables as system_catalog_tables
from docmind_api.settings import (
    DatabaseSettings,
    get_database_migration_settings,
    get_database_settings,
)

config = context.config

if config.config_file_name is not None and not config.attributes.get("skip_logging_config"):
    fileConfig(config.config_file_name)

target_metadata = auth_tables.users_table.metadata
if document_type_tables.document_types_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if attribute_tables.attribute_definitions_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if dictionary_tables.dictionaries_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if dictionary_tables.dictionary_fields_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if dictionary_tables.dictionary_entries_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if attribute_requirement_tables.attribute_requirements_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if document_tables.documents_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if document_deletion_tables.document_deletion_operations_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if (
    connector_document_archive_tables.connector_document_archives_table.metadata
    is not target_metadata
):
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if document_review_tables.document_reviews_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if document_review_tables.document_review_versions_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if ocr_pipeline_tables.ocr_pipeline_definitions_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if ocr_pipeline_tables.ocr_pipeline_definition_versions_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if ocr_pipeline_tables.ocr_pipeline_definition_names_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if ocr_pipeline_tables.ocr_pipeline_definition_audit_events_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if ocr_pipeline_run_tables.ocr_pipeline_runs_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if ocr_pipeline_run_tables.ocr_pipeline_run_outbox_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if system_catalog_tables.system_catalog_extension_fields_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if system_catalog_tables.document_type_extension_values_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if system_catalog_tables.system_catalog_display_modes_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")
if system_catalog_tables.system_catalog_display_mode_parts_table.metadata is not target_metadata:
    raise RuntimeError("API SQLAlchemy metadata registry is inconsistent.")


def _database_url() -> str:
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url is not None and configured_url.strip():
        return configured_url.strip()

    return get_database_settings().url


def _database_settings() -> DatabaseSettings:
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url is not None and configured_url.strip():
        return DatabaseSettings(
            url=configured_url.strip(),
            echo=False,
            pool_pre_ping=True,
        )

    return get_database_settings()


def run_migrations_offline() -> None:
    """Run migrations without a live database connection."""

    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure Alembic against a synchronous connection proxy."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()
        migration_settings = get_database_migration_settings()
        apply_runtime_database_permissions(
            connection,
            runtime_principal_name=migration_settings.runtime_principal_name,
            runtime_principal_object_id=migration_settings.runtime_principal_object_id,
        )


async def run_async_migrations() -> None:
    """Run migrations through SQLAlchemy's async engine."""

    connectable = create_database_engine(
        _database_settings(),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations with a live database connection."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
