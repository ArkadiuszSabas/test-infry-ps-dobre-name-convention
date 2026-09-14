"""Pinned SQLAlchemy model contract for dedicated workspace schemas."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

import sqlalchemy as sa
from sqlalchemy import ForeignKeyConstraint, MetaData, Table

from docmind_api.infrastructure.persistence.attribute_requirements.tables import (
    attribute_requirements_table,
)
from docmind_api.infrastructure.persistence.connectors.document_archive_tables import (
    connector_document_archives_table,
)
from docmind_api.infrastructure.persistence.document_review.tables import (
    document_approval_decisions_table,
    document_approval_settings_table,
    document_approval_workflows_table,
    document_review_versions_table,
    document_reviews_table,
)
from docmind_api.infrastructure.persistence.documents.deletion_tables import (
    document_deletion_operations_table,
)
from docmind_api.infrastructure.persistence.documents.tables import (
    document_type_change_audit_events_table,
    documents_table,
)
from docmind_api.infrastructure.persistence.ocr_pipeline_runs.tables import (
    ocr_pipeline_run_attempts_table,
    ocr_pipeline_run_outbox_table,
    ocr_pipeline_runs_table,
)

PUBLIC_SCHEMA = "public"
EXPECTED_LOCAL_MODEL_FINGERPRINT = (
    "2aad225c73ff59106b334d13a8ce8e89da7ca4d6119be3ba02622f58c6ae8914"
)

_LOCAL_TABLES = (
    attribute_requirements_table,
    documents_table,
    document_type_change_audit_events_table,
    document_deletion_operations_table,
    document_reviews_table,
    document_review_versions_table,
    document_approval_workflows_table,
    document_approval_decisions_table,
    document_approval_settings_table,
    connector_document_archives_table,
    ocr_pipeline_runs_table,
    ocr_pipeline_run_attempts_table,
    ocr_pipeline_run_outbox_table,
)
LOCAL_TABLE_NAMES = frozenset(table.name for table in _LOCAL_TABLES)
_SHARED_FOREIGN_TABLE_NAMES = frozenset(
    {
        "attribute_definitions",
        "document_types",
        "ocr_pipeline_definitions",
        "ocr_pipeline_definition_versions",
    }
)


def copy_workspace_local_tables(metadata: MetaData, schema_name: str) -> tuple[Table, ...]:
    """Copy the pinned local model into one dedicated schema."""

    _register_shared_reference_tables(metadata)
    copied_tables = tuple(
        table.to_metadata(
            metadata,
            schema=schema_name,
            referred_schema_fn=_referred_schema(schema_name),
        )
        for table in _LOCAL_TABLES
    )
    copied_by_name = {table.name: table for table in copied_tables}

    # These values changed only in Alembic migrations, not in the SQLAlchemy
    # declarations. Preserve the final public physical contract without
    # replaying the historical migration stream under a dedicated schema.
    copied_by_name[
        "attribute_requirements"
    ].c.include_metadata_in_context_resolver.server_default = None
    copied_by_name["ocr_pipeline_run_outbox"].c.available_at.server_default = sa.DefaultClause(
        sa.text("now()")
    )
    copied_by_name["document_review_versions"].c.is_reprocessing.server_default = None
    return copied_tables


def local_model_fingerprint() -> str:
    """Return the stable source-model fingerprint guarded by ``workspace_m1``."""

    table_contracts: list[tuple[object, ...]] = []
    for table in _LOCAL_TABLES:
        columns = tuple(
            (
                column.name,
                str(column.type),
                column.nullable,
                column.primary_key,
                _server_default_contract(column),
            )
            for column in table.columns
        )
        constraints = tuple(
            sorted(_constraint_contract(constraint) for constraint in table.constraints)
        )
        indexes = tuple(
            sorted(
                (
                    index.name,
                    index.unique,
                    tuple(str(expression) for expression in index.expressions),
                    str(index.dialect_options["postgresql"].get("where")),
                )
                for index in table.indexes
            )
        )
        table_contracts.append((table.name, columns, constraints, indexes))
    encoded_contract = json.dumps(table_contracts, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded_contract.encode("utf-8")).hexdigest()


def require_pinned_local_model() -> None:
    """Fail closed when source declarations drift from the pinned baseline."""

    if local_model_fingerprint() != EXPECTED_LOCAL_MODEL_FINGERPRINT:
        raise RuntimeError(
            "Workspace local model no longer matches the pinned workspace_m1 baseline. "
            "Add a reviewed dedicated-schema delta instead of changing this baseline."
        )


def _constraint_contract(constraint: sa.Constraint) -> tuple[object, ...]:
    if isinstance(constraint, ForeignKeyConstraint):
        return (
            "foreign_key",
            constraint.name,
            tuple(
                (
                    foreign_key.parent.name,
                    foreign_key.target_fullname,
                    foreign_key.ondelete,
                    foreign_key.deferrable,
                    foreign_key.initially,
                    foreign_key.use_alter,
                )
                for foreign_key in constraint.elements
            ),
        )
    if isinstance(constraint, sa.CheckConstraint):
        return ("check", constraint.name, str(constraint.sqltext))
    if isinstance(constraint, (sa.PrimaryKeyConstraint, sa.UniqueConstraint)):
        return (
            type(constraint).__name__,
            constraint.name,
            tuple(column.name for column in constraint.columns),
        )
    raise RuntimeError(f"Unsupported local-table constraint: {type(constraint).__name__}.")


def _server_default_contract(column: sa.Column[object]) -> str | None:
    if column.server_default is None:
        return None
    return str(column.server_default)


def _register_shared_reference_tables(metadata: MetaData) -> None:
    """Register DDL-only public FK targets without creating or copying them."""

    Table(
        "attribute_definitions",
        metadata,
        sa.Column("id", sa.UUID(), primary_key=True),
        schema=PUBLIC_SCHEMA,
    )
    Table(
        "document_types",
        metadata,
        sa.Column("id", sa.UUID(), primary_key=True),
        schema=PUBLIC_SCHEMA,
    )
    Table(
        "ocr_pipeline_definitions",
        metadata,
        sa.Column("id", sa.UUID(), primary_key=True),
        schema=PUBLIC_SCHEMA,
    )
    Table(
        "ocr_pipeline_definition_versions",
        metadata,
        sa.Column("definition_id", sa.UUID(), primary_key=True),
        sa.Column("version_number", sa.Integer(), primary_key=True),
        schema=PUBLIC_SCHEMA,
    )


def _referred_schema(schema_name: str) -> Callable[..., str]:
    def resolve(
        _table: Table,
        _target_schema: str | None,
        constraint: ForeignKeyConstraint,
        referred_schema: str | None,
    ) -> str:
        if referred_schema is not None:
            return referred_schema

        referred_table_name = constraint.elements[0].target_fullname.split(".")[-2]
        if referred_table_name in LOCAL_TABLE_NAMES:
            return schema_name
        if referred_table_name in _SHARED_FOREIGN_TABLE_NAMES:
            return PUBLIC_SCHEMA
        raise RuntimeError(
            "Workspace schema baseline encountered an unclassified foreign-key target: "
            f"{referred_table_name}."
        )

    return resolve
