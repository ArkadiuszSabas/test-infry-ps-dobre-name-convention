"""PostgreSQL runtime privilege helpers used by Alembic migrations."""

from collections.abc import Mapping
from typing import Any, Protocol

import sqlalchemy as sa


class RuntimePermissionConnection(Protocol):
    """Synchronous SQLAlchemy connection subset used by migration grants."""

    def execute(
        self,
        statement: Any,
        parameters: Mapping[str, object] | None = None,
    ) -> Any: ...

    def scalar(
        self,
        statement: Any,
        parameters: Mapping[str, object] | None = None,
    ) -> object: ...


def apply_runtime_database_permissions(
    connection: RuntimePermissionConnection,
    *,
    runtime_principal_name: str | None,
    runtime_principal_object_id: str | None = None,
) -> None:
    """Grant runtime DML privileges without giving the API schema migration rights."""

    if runtime_principal_name is None:
        return

    _ensure_entra_database_principal(
        connection,
        runtime_principal_name,
        runtime_principal_object_id,
    )
    transfer_runtime_owned_objects_to_migrator(connection, runtime_principal_name)
    runtime_role = _quote_database_identifier(connection, runtime_principal_name)
    for statement in _runtime_permission_statements(runtime_role):
        connection.execute(sa.text(statement))


def _ensure_entra_database_principal(
    connection: RuntimePermissionConnection,
    runtime_principal_name: str,
    runtime_principal_object_id: str | None,
) -> None:
    if runtime_principal_object_id is not None:
        _ensure_entra_database_principal_by_object_id(
            connection,
            runtime_principal_name,
            runtime_principal_object_id,
        )
        return

    if not _database_role_exists(connection, runtime_principal_name):
        _ensure_entra_database_principal_by_name(connection, runtime_principal_name)


def _database_role_exists(
    connection: RuntimePermissionConnection,
    runtime_principal_name: str,
) -> bool:
    exists = connection.scalar(
        sa.text(
            """
            select exists (
                select 1
                from pg_catalog.pg_roles
                where rolname = :runtime_principal_name
            )
            """,
        ),
        {"runtime_principal_name": runtime_principal_name},
    )
    return bool(exists)


def _ensure_entra_database_principal_by_name(
    connection: RuntimePermissionConnection,
    runtime_principal_name: str,
) -> None:
    connection.execute(
        sa.text(
            """
            select pg_catalog.pgaadauth_create_principal(
                :runtime_principal_name,
                false,
                false
            )
            where not exists (
                select 1
                from pg_catalog.pg_roles
                where rolname = :runtime_principal_name
            )
            """,
        ),
        {"runtime_principal_name": runtime_principal_name},
    )


def _ensure_entra_database_principal_by_object_id(
    connection: RuntimePermissionConnection,
    runtime_principal_name: str,
    runtime_principal_object_id: str,
) -> None:
    connection.execute(
        sa.text(
            "select pg_catalog.set_config("
            "'docmind.runtime_principal_name', :runtime_principal_name, true)",
        ),
        {"runtime_principal_name": runtime_principal_name},
    )
    connection.execute(
        sa.text(
            "select pg_catalog.set_config("
            "'docmind.runtime_principal_object_id', :runtime_principal_object_id, true)",
        ),
        {"runtime_principal_object_id": runtime_principal_object_id},
    )
    connection.execute(
        sa.text(
            """
            do $docmind$
            declare
                runtime_role text := current_setting(
                    'docmind.runtime_principal_name',
                    true
                );
                runtime_object_id text := current_setting(
                    'docmind.runtime_principal_object_id',
                    true
                );
            begin
                if runtime_role is null or runtime_role = '' then
                    raise exception 'Missing DocMind runtime database principal.';
                end if;

                if runtime_object_id is null or runtime_object_id = '' then
                    raise exception 'Missing DocMind runtime database principal Object ID.';
                end if;

                if not exists (
                    select 1
                    from pg_catalog.pg_roles
                    where rolname = runtime_role
                ) then
                    execute format(
                        'create role %I with login',
                        runtime_role
                    );
                end if;

                execute format(
                    'security label for "pgaadauth" on role %I is %L',
                    runtime_role,
                    'aadauth,oid=' || runtime_object_id || ',type=service'
                );
            end
            $docmind$;
            """,
        ),
    )


def transfer_runtime_owned_objects_to_migrator(
    connection: RuntimePermissionConnection,
    runtime_principal_name: str,
) -> None:
    """Move runtime-owned public schema objects back to the current migrator role."""

    connection.execute(
        sa.text(
            "select pg_catalog.set_config("
            "'docmind.runtime_principal_name', :runtime_principal_name, true)",
        ),
        {"runtime_principal_name": runtime_principal_name},
    )
    connection.execute(
        sa.text(
            """
            do $docmind$
            declare
                runtime_role name := current_setting(
                    'docmind.runtime_principal_name',
                    true
                )::name;
                migrator_role name := current_user;
                object_record record;
            begin
                if runtime_role is null or runtime_role = '' then
                    raise exception 'Missing DocMind runtime database principal.';
                end if;

                if exists (
                    select 1
                    from pg_catalog.pg_namespace namespace
                    join pg_catalog.pg_roles owner_role
                        on owner_role.oid = namespace.nspowner
                    where namespace.nspname = 'public'
                      and owner_role.rolname = runtime_role
                ) then
                    execute format('alter schema public owner to %I', migrator_role);
                end if;

                for object_record in
                    select
                        object_class.relkind,
                        format(
                            '%I.%I',
                            namespace.nspname,
                            object_class.relname
                        ) as qualified_name
                    from pg_catalog.pg_class object_class
                    join pg_catalog.pg_namespace namespace
                        on namespace.oid = object_class.relnamespace
                    join pg_catalog.pg_roles owner_role
                        on owner_role.oid = object_class.relowner
                    where namespace.nspname = 'public'
                      and owner_role.rolname = runtime_role
                      and object_class.relkind in ('r', 'p', 'S', 'v', 'm', 'f')
                loop
                    execute format(
                        'alter %s %s owner to %I',
                        case object_record.relkind
                            when 'S' then 'sequence'
                            when 'v' then 'view'
                            when 'm' then 'materialized view'
                            when 'f' then 'foreign table'
                            else 'table'
                        end,
                        object_record.qualified_name,
                        migrator_role
                    );
                end loop;

                for object_record in
                    select
                        format(
                            '%I.%I(%s)',
                            namespace.nspname,
                            procedure.proname,
                            pg_catalog.pg_get_function_identity_arguments(procedure.oid)
                        ) as qualified_signature
                    from pg_catalog.pg_proc procedure
                    join pg_catalog.pg_namespace namespace
                        on namespace.oid = procedure.pronamespace
                    join pg_catalog.pg_roles owner_role
                        on owner_role.oid = procedure.proowner
                    where namespace.nspname = 'public'
                      and owner_role.rolname = runtime_role
                      and procedure.prokind = 'f'
                loop
                    execute format(
                        'alter function %s owner to %I',
                        object_record.qualified_signature,
                        migrator_role
                    );
                end loop;
            end
            $docmind$;
            """,
        ),
    )


def _quote_database_identifier(
    connection: RuntimePermissionConnection,
    value: str,
) -> str:
    quoted_identifier = connection.scalar(
        sa.text("select pg_catalog.quote_ident(:identifier)"),
        {"identifier": value},
    )
    if not isinstance(quoted_identifier, str) or not quoted_identifier:
        raise RuntimeError("Failed to quote runtime database principal name.")

    return quoted_identifier


def _runtime_permission_statements(runtime_role: str) -> tuple[str, ...]:
    table_privileges = "select, insert, update, delete"
    sequence_privileges = "usage, select"

    return (
        f"revoke azure_pg_admin from {runtime_role}",
        "revoke create on schema public from public",
        f"grant usage on schema public to {runtime_role}",
        f"grant {table_privileges} on all tables in schema public to {runtime_role}",
        f"grant {sequence_privileges} on all sequences in schema public to {runtime_role}",
        f"grant execute on all functions in schema public to {runtime_role}",
        (
            "alter default privileges in schema public "
            f"grant {table_privileges} on tables to {runtime_role}"
        ),
        (
            "alter default privileges in schema public "
            f"grant {sequence_privileges} on sequences to {runtime_role}"
        ),
        (f"alter default privileges in schema public grant execute on functions to {runtime_role}"),
        f"revoke all privileges on table alembic_version from {runtime_role}",
    )
