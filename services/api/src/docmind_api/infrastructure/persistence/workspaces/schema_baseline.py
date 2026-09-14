"""Pinned dedicated-schema baseline for one registered workspace.

The API Alembic stream remains the sole owner of ``public``. This module
preflights that stream, creates an empty registry-derived schema, and invokes
the dedicated local Alembic stream through the caller's connection and
transaction. It never commits or changes the connection search path.
"""

from __future__ import annotations

import re

import sqlalchemy as sa
from sqlalchemy import MetaData
from sqlalchemy.engine import Connection

from docmind_api.infrastructure.persistence.migrations import run_workspace_migrations_to_head
from docmind_api.infrastructure.persistence.workspaces.schema_baseline_verification import (
    create_workspace_dependency_table,
    verify_workspace_schema_physical_contract,
)
from docmind_api.infrastructure.persistence.workspaces.schema_model import (
    EXPECTED_LOCAL_MODEL_FINGERPRINT as EXPECTED_LOCAL_MODEL_FINGERPRINT,
)
from docmind_api.infrastructure.persistence.workspaces.schema_model import (
    LOCAL_TABLE_NAMES as LOCAL_TABLE_NAMES,
)
from docmind_api.infrastructure.persistence.workspaces.schema_model import (
    copy_workspace_local_tables,
    require_pinned_local_model,
)
from docmind_api.infrastructure.persistence.workspaces.schema_model import (
    local_model_fingerprint as local_model_fingerprint,
)

REQUIRED_SHARED_REVISION = "20260910_0052"
WORKSPACE_PROVISIONING_TARGET_REVISION = "workspace-m1"
LOCAL_BASELINE_REVISION = "workspace_m1"
WORKSPACE_VERSION_TABLE = "workspace_alembic_version"
WORKSPACE_SHARED_DEPENDENCY_TABLE = "workspace_schema_dependencies"

_EXPECTED_DELETION_FENCE_TRIGGER_EVENTS = {
    "trg_connector_document_archives_deletion_fence": frozenset({"INSERT"}),
    "trg_document_approval_decisions_deletion_fence": frozenset({"INSERT", "UPDATE"}),
    "trg_document_approval_workflows_deletion_fence": frozenset({"INSERT", "UPDATE"}),
    "trg_document_review_versions_deletion_fence": frozenset({"INSERT", "UPDATE"}),
    "trg_document_reviews_deletion_fence": frozenset({"INSERT", "UPDATE"}),
    "trg_document_type_change_audit_events_deletion_fence": frozenset({"INSERT", "UPDATE"}),
    "trg_ocr_pipeline_runs_deletion_fence": frozenset({"INSERT", "UPDATE"}),
}

_WORKSPACE_SCHEMA_NAME_PATTERN = re.compile(r"^ws_[0-9a-f]{32}$")
_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_REJECT_DOCUMENT_WRITE_WHILE_DELETING_FUNCTION = """
    create function %(workspace_schema)s.reject_document_write_while_deleting()
    returns trigger language plpgsql as $$
    begin
        if exists (
            select 1 from %(workspace_schema)s.document_deletion_operations
            where document_id = new.document_id and stage <> 'completed'
        ) then
            raise exception 'DOCUMENT_DELETE_IN_PROGRESS' using errcode = '23514';
        end if;
        return new;
    end;
    $$;
"""
_REJECT_REVIEW_VERSION_WRITE_WHILE_DELETING_FUNCTION = """
    create function %(workspace_schema)s.reject_review_version_write_while_deleting()
    returns trigger language plpgsql as $$
    begin
        if exists (
            select 1 from %(workspace_schema)s.document_reviews review
            join %(workspace_schema)s.document_deletion_operations deletion
              on deletion.document_id = review.document_id
            where review.id = new.review_id and deletion.stage <> 'completed'
        ) then
            raise exception 'DOCUMENT_DELETE_IN_PROGRESS' using errcode = '23514';
        end if;
        return new;
    end;
    $$;
"""


def apply_workspace_schema_baseline(
    connection: Connection,
    *,
    schema_name: str,
    runtime_principal_name: str | None,
) -> None:
    """Create the baseline inside the caller's existing transaction.

    The later provisioning executor supplies the workspace binding only after
    locking and revalidating its shared registry record. Existing schemas are
    rejected here; retry/readback and footprint repair are executor concerns.
    """

    _require_workspace_schema_name(schema_name)
    require_pinned_local_model()
    _require_shared_revision(connection)
    if _schema_exists(connection, schema_name):
        raise RuntimeError(f"Workspace schema already exists: {schema_name}.")

    connection.execute(sa.text(f"create schema {_quote_identifier(schema_name)}"))
    run_workspace_migrations_to_head(connection=connection, schema_name=schema_name)
    if runtime_principal_name is not None:
        apply_workspace_schema_runtime_permissions(
            connection,
            schema_name=schema_name,
            runtime_principal_name=runtime_principal_name,
        )


def create_workspace_schema_objects(connection: Connection, *, schema_name: str) -> None:
    """Create the revision's local objects after Alembic owns its version table."""

    _require_workspace_schema_name(schema_name)
    baseline_metadata = MetaData()
    local_tables = copy_workspace_local_tables(baseline_metadata, schema_name)
    dependency_table = create_workspace_dependency_table(
        baseline_metadata,
        schema_name=schema_name,
        table_name=WORKSPACE_SHARED_DEPENDENCY_TABLE,
    )
    baseline_metadata.create_all(
        connection, tables=(*local_tables, dependency_table), checkfirst=False
    )
    connection.execute(
        dependency_table.insert().values(
            dependency_name="public_alembic",
            shared_revision=REQUIRED_SHARED_REVISION,
        )
    )
    _create_deletion_fence_functions_and_triggers(connection, schema_name)


def apply_workspace_schema_runtime_permissions(
    connection: Connection,
    *,
    schema_name: str,
    runtime_principal_name: str,
) -> None:
    """Grant local runtime DML without granting schema or revision-record control."""

    _require_workspace_schema_name(schema_name)
    runtime_role = _quote_database_identifier(connection, runtime_principal_name)
    quoted_schema_name = _quote_identifier(schema_name)
    table_list = ", ".join(
        f"{quoted_schema_name}.{_quote_identifier(table_name)}"
        for table_name in sorted(LOCAL_TABLE_NAMES)
    )

    for statement in (
        f"revoke all privileges on schema {quoted_schema_name} from public",
        f"revoke all privileges on all tables in schema {quoted_schema_name} from public",
        f"revoke all privileges on all sequences in schema {quoted_schema_name} from public",
        f"revoke all privileges on all functions in schema {quoted_schema_name} from public",
        f"revoke create on schema {quoted_schema_name} from {runtime_role}",
        f"grant usage on schema {quoted_schema_name} to {runtime_role}",
        f"grant select, insert, update, delete on table {table_list} to {runtime_role}",
        f"grant usage, select on all sequences in schema {quoted_schema_name} to {runtime_role}",
        f"grant execute on all functions in schema {quoted_schema_name} to {runtime_role}",
        (
            "revoke all privileges on table "
            f"{quoted_schema_name}.{_quote_identifier(WORKSPACE_SHARED_DEPENDENCY_TABLE)} "
            f"from {runtime_role}"
        ),
        (
            "revoke all privileges on table "
            f"{quoted_schema_name}.{_quote_identifier(WORKSPACE_VERSION_TABLE)} from {runtime_role}"
        ),
    ):
        connection.execute(sa.text(statement))


def verify_workspace_schema_baseline(connection: Connection, *, schema_name: str) -> None:
    """Fail closed unless the dedicated schema matches the pinned M1 footprint."""

    _require_workspace_schema_name(schema_name)
    require_pinned_local_model()
    _require_shared_revision(connection)
    table_rows = connection.execute(
        sa.text(
            """
            select table_name
            from information_schema.tables
            where table_schema = :schema_name
            """
        ),
        {"schema_name": schema_name},
    )
    actual_tables = {str(row[0]) for row in table_rows}
    expected_tables = set(LOCAL_TABLE_NAMES) | {
        WORKSPACE_SHARED_DEPENDENCY_TABLE,
        WORKSPACE_VERSION_TABLE,
    }
    if actual_tables != expected_tables:
        raise RuntimeError("Workspace schema footprint does not match the pinned baseline.")

    _require_schema_owner(connection, schema_name)
    verify_workspace_schema_physical_contract(
        connection,
        schema_name=schema_name,
        dependency_table_name=WORKSPACE_SHARED_DEPENDENCY_TABLE,
        version_table_name=WORKSPACE_VERSION_TABLE,
    )

    dependency_table = sa.table(
        WORKSPACE_SHARED_DEPENDENCY_TABLE,
        sa.column("dependency_name"),
        sa.column("shared_revision"),
        schema=schema_name,
    )
    dependency_rows = connection.execute(
        sa.select(
            dependency_table.c.dependency_name,
            dependency_table.c.shared_revision,
        )
    ).all()
    if dependency_rows != [("public_alembic", REQUIRED_SHARED_REVISION)]:
        raise RuntimeError("Workspace schema dependency record does not match the pinned baseline.")

    version_table = sa.table(
        WORKSPACE_VERSION_TABLE,
        sa.column("version_num"),
        schema=schema_name,
    )
    revisions = connection.execute(sa.select(version_table.c.version_num)).scalars().all()
    if revisions != [LOCAL_BASELINE_REVISION]:
        raise RuntimeError("Workspace schema revision does not match the pinned baseline.")

    trigger_rows = connection.execute(
        sa.text(
            """
            select trigger_name, event_manipulation
            from information_schema.triggers
            where trigger_schema = :schema_name
            """
        ),
        {"schema_name": schema_name},
    )
    trigger_events: dict[str, set[str]] = {}
    for trigger_name, event_manipulation in trigger_rows:
        trigger_events.setdefault(str(trigger_name), set()).add(str(event_manipulation))
    if {
        trigger_name: frozenset(events) for trigger_name, events in trigger_events.items()
    } != _EXPECTED_DELETION_FENCE_TRIGGER_EVENTS:
        raise RuntimeError("Workspace schema trigger footprint does not match the pinned baseline.")


def _require_schema_owner(connection: Connection, schema_name: str) -> None:
    schema_owner = connection.scalar(
        sa.text(
            """
            select owner_role.rolname
            from pg_catalog.pg_namespace namespace
            join pg_catalog.pg_roles owner_role on owner_role.oid = namespace.nspowner
            where namespace.nspname = :schema_name
            """
        ),
        {"schema_name": schema_name},
    )
    current_user = connection.scalar(sa.text("select current_user"))
    if not isinstance(schema_owner, str) or schema_owner != current_user:
        raise RuntimeError("Workspace schema is not owned by the current migrator principal.")


def _create_deletion_fence_functions_and_triggers(
    connection: Connection,
    schema_name: str,
) -> None:
    quoted_schema_name = _quote_identifier(schema_name)
    connection.execute(
        sa.DDL(
            _REJECT_DOCUMENT_WRITE_WHILE_DELETING_FUNCTION,
            context={"workspace_schema": quoted_schema_name},
        )
    )
    connection.execute(
        sa.DDL(
            _REJECT_REVIEW_VERSION_WRITE_WHILE_DELETING_FUNCTION,
            context={"workspace_schema": quoted_schema_name},
        )
    )
    for table_name in (
        "ocr_pipeline_runs",
        "document_reviews",
        "document_approval_workflows",
        "document_approval_decisions",
        "document_type_change_audit_events",
    ):
        connection.execute(
            sa.text(
                f"""
                create trigger trg_{table_name}_deletion_fence
                before insert or update on {quoted_schema_name}.{_quote_identifier(table_name)}
                for each row execute function
                    {quoted_schema_name}.reject_document_write_while_deleting();
                """
            )
        )
    connection.execute(
        sa.text(
            f"""
            create trigger trg_connector_document_archives_deletion_fence
            before insert on {quoted_schema_name}.connector_document_archives
            for each row execute function
                {quoted_schema_name}.reject_document_write_while_deleting();
            """
        )
    )
    connection.execute(
        sa.text(
            f"""
            create trigger trg_document_review_versions_deletion_fence
            before insert or update on {quoted_schema_name}.document_review_versions
            for each row execute function
                {quoted_schema_name}.reject_review_version_write_while_deleting();
            """
        )
    )


def _require_shared_revision(connection: Connection) -> None:
    installed_revision = connection.scalar(
        sa.text("select version_num from public.alembic_version")
    )
    if installed_revision != REQUIRED_SHARED_REVISION:
        raise RuntimeError(
            "Workspace schema baseline requires public Alembic revision "
            f"{REQUIRED_SHARED_REVISION}; found {installed_revision!r}."
        )


def _require_workspace_schema_name(schema_name: str) -> None:
    if not _WORKSPACE_SCHEMA_NAME_PATTERN.fullmatch(schema_name):
        raise ValueError("Workspace schema names must be registry-derived ws_<uuidhex> values.")


def _schema_exists(connection: Connection, schema_name: str) -> bool:
    return bool(
        connection.scalar(
            sa.text(
                "select exists (select 1 from pg_catalog.pg_namespace where nspname = :schema_name)"
            ),
            {"schema_name": schema_name},
        )
    )


def _quote_identifier(value: str) -> str:
    if not _IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Unsupported PostgreSQL identifier: {value!r}.")
    return f'"{value}"'


def _quote_database_identifier(connection: Connection, value: str) -> str:
    quoted_identifier = connection.scalar(
        sa.text("select pg_catalog.quote_ident(:identifier)"),
        {"identifier": value},
    )
    if not isinstance(quoted_identifier, str) or not quoted_identifier:
        raise RuntimeError("Failed to quote runtime database principal name.")
    return quoted_identifier
