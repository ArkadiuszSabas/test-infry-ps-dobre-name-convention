"""Physical PostgreSQL contract verification for a dedicated workspace schema."""

from __future__ import annotations

from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy import MetaData, Table
from sqlalchemy.engine import Connection
from sqlalchemy.engine.interfaces import (
    ReflectedColumn,
    ReflectedForeignKeyConstraint,
    ReflectedIndex,
)

from docmind_api.infrastructure.persistence.workspaces.schema_model import (
    PUBLIC_SCHEMA,
    copy_workspace_local_tables,
)
from docmind_api.infrastructure.persistence.workspaces.schema_sql_contract import (
    check_constraint_contract,
    sql_contract,
)


def create_workspace_dependency_table(
    metadata: MetaData,
    *,
    schema_name: str,
    table_name: str,
) -> Table:
    """Define the baseline-owned dependency record alongside copied local tables."""

    return Table(
        table_name,
        metadata,
        sa.Column("dependency_name", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("shared_revision", sa.String(length=128), nullable=False),
        sa.Column(
            "installed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.CheckConstraint("dependency_name = 'public_alembic'", name="dependency_name_supported"),
        sa.CheckConstraint("length(trim(shared_revision)) > 0", name="shared_revision_not_empty"),
        schema=schema_name,
    )


def verify_workspace_schema_physical_contract(
    connection: Connection,
    *,
    schema_name: str,
    dependency_table_name: str,
    version_table_name: str,
) -> None:
    """Fail closed unless columns, constraints, and indexes match the M1 model."""

    _require_expected_columns(
        connection,
        schema_name=schema_name,
        dependency_table_name=dependency_table_name,
        version_table_name=version_table_name,
    )
    _require_expected_constraints(
        connection,
        schema_name=schema_name,
        dependency_table_name=dependency_table_name,
        version_table_name=version_table_name,
    )
    _require_expected_indexes(
        connection,
        schema_name=schema_name,
        dependency_table_name=dependency_table_name,
        version_table_name=version_table_name,
    )


def _require_expected_columns(
    connection: Connection,
    *,
    schema_name: str,
    dependency_table_name: str,
    version_table_name: str,
) -> None:
    inspector = sa.inspect(connection)
    for table in _expected_baseline_tables(
        schema_name=schema_name,
        dependency_table_name=dependency_table_name,
        version_table_name=version_table_name,
    ):
        expected_columns = {
            column.name: _expected_column_contract(connection, column) for column in table.columns
        }
        actual_columns = {
            str(column["name"]): _reflected_column_contract(connection, column)
            for column in inspector.get_columns(table.name, schema=schema_name)
        }
        if actual_columns != expected_columns:
            raise RuntimeError(
                "Workspace schema column footprint does not match the pinned baseline."
            )


def _require_expected_constraints(
    connection: Connection,
    *,
    schema_name: str,
    dependency_table_name: str,
    version_table_name: str,
) -> None:
    inspector = sa.inspect(connection)
    for table in _expected_baseline_tables(
        schema_name=schema_name,
        dependency_table_name=dependency_table_name,
        version_table_name=version_table_name,
    ):
        primary_key = tuple(column.name for column in table.primary_key.columns)
        actual_primary_key = tuple(
            str(column_name)
            for column_name in inspector.get_pk_constraint(table.name, schema=schema_name).get(
                "constrained_columns", ()
            )
        )
        if actual_primary_key != primary_key:
            raise RuntimeError(
                "Workspace schema primary-key footprint does not match the pinned baseline."
            )

        expected_unique_constraints = frozenset(
            tuple(column.name for column in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, sa.UniqueConstraint)
        )
        actual_unique_constraints = frozenset(
            tuple(str(column_name) for column_name in constraint.get("column_names", ()))
            for constraint in inspector.get_unique_constraints(table.name, schema=schema_name)
        )
        if actual_unique_constraints != expected_unique_constraints:
            raise RuntimeError(
                "Workspace schema unique-constraint footprint does not match the pinned baseline."
            )

        expected_checks = frozenset(
            check_constraint_contract(constraint.sqltext)
            for constraint in table.constraints
            if isinstance(constraint, sa.CheckConstraint)
        )
        actual_checks = frozenset(
            check_constraint_contract(constraint.get("sqltext"))
            for constraint in inspector.get_check_constraints(table.name, schema=schema_name)
        )
        if actual_checks != expected_checks:
            raise RuntimeError(
                "Workspace schema check-constraint footprint does not match the pinned baseline."
            )

        expected_foreign_keys = frozenset(
            _expected_foreign_key_contract(constraint)
            for constraint in table.constraints
            if isinstance(constraint, sa.ForeignKeyConstraint)
        )
        actual_foreign_keys = frozenset(
            _reflected_foreign_key_contract(foreign_key)
            for foreign_key in inspector.get_foreign_keys(table.name, schema=schema_name)
        )
        if actual_foreign_keys != expected_foreign_keys:
            raise RuntimeError(
                "Workspace schema foreign-key footprint does not match the pinned baseline."
            )


def _require_expected_indexes(
    connection: Connection,
    *,
    schema_name: str,
    dependency_table_name: str,
    version_table_name: str,
) -> None:
    inspector = sa.inspect(connection)
    for table in _expected_baseline_tables(
        schema_name=schema_name,
        dependency_table_name=dependency_table_name,
        version_table_name=version_table_name,
    ):
        expected_indexes = frozenset(
            (
                index.name,
                index.unique,
                tuple(_index_expression_contract(expression) for expression in index.expressions),
                check_constraint_contract(index.dialect_options["postgresql"].get("where")),
            )
            for index in table.indexes
        )
        actual_indexes = frozenset(
            _reflected_index_contract(index)
            for index in inspector.get_indexes(table.name, schema=schema_name)
            if index.get("duplicates_constraint") is None
        )
        if actual_indexes != expected_indexes:
            raise RuntimeError(
                "Workspace schema index footprint does not match the pinned baseline."
            )


def _expected_baseline_tables(
    *,
    schema_name: str,
    dependency_table_name: str,
    version_table_name: str,
) -> tuple[Table, ...]:
    metadata = MetaData()
    local_tables = copy_workspace_local_tables(metadata, schema_name)
    dependency_table = create_workspace_dependency_table(
        metadata,
        schema_name=schema_name,
        table_name=dependency_table_name,
    )
    version_table = Table(
        version_table_name,
        metadata,
        sa.Column("version_num", sa.String(length=32), primary_key=True, nullable=False),
        schema=schema_name,
    )
    return (*local_tables, dependency_table, version_table)


def _expected_column_contract(
    connection: Connection,
    column: sa.Column[Any],
) -> tuple[str, str, bool, str | None]:
    nullable = column.nullable
    if nullable is None:
        raise RuntimeError("Workspace schema column footprint does not match the pinned baseline.")
    return (
        column.name,
        _type_contract(connection, column.type),
        nullable,
        sql_contract(column.server_default),
    )


def _reflected_column_contract(
    connection: Connection,
    column: ReflectedColumn,
) -> tuple[str, str, bool, str | None]:
    return (
        str(column["name"]),
        _type_contract(connection, column["type"]),
        column["nullable"],
        sql_contract(column.get("default")),
    )


def _type_contract(connection: Connection, type_: sa.types.TypeEngine[Any]) -> str:
    return sql_contract(connection.dialect.type_compiler.process(type_)) or ""


def _expected_foreign_key_contract(
    constraint: sa.ForeignKeyConstraint,
) -> tuple[
    tuple[str, ...],
    str | None,
    str,
    tuple[str, ...],
    str | None,
    str | None,
    bool | None,
    str | None,
]:
    elements = tuple(constraint.elements)
    first_target = elements[0].column.table
    return (
        tuple(element.parent.name for element in elements),
        first_target.schema,
        first_target.name,
        tuple(element.column.name for element in elements),
        sql_contract(constraint.onupdate),
        sql_contract(constraint.ondelete),
        constraint.deferrable,
        _initially_contract(constraint.initially),
    )


def _reflected_foreign_key_contract(
    foreign_key: ReflectedForeignKeyConstraint,
) -> tuple[
    tuple[str, ...],
    str | None,
    str,
    tuple[str, ...],
    str | None,
    str | None,
    bool | None,
    str | None,
]:
    options_value: object = foreign_key.get("options")
    options = cast(dict[str, object], options_value) if isinstance(options_value, dict) else {}
    return (
        tuple(str(column_name) for column_name in foreign_key.get("constrained_columns", ())),
        _optional_string(foreign_key.get("referred_schema")) or PUBLIC_SCHEMA,
        foreign_key["referred_table"],
        tuple(str(column_name) for column_name in foreign_key.get("referred_columns", ())),
        sql_contract(options.get("onupdate")),
        sql_contract(options.get("ondelete")),
        _optional_bool(options.get("deferrable")),
        _initially_contract(options.get("initially")),
    )


def _reflected_index_contract(
    index: ReflectedIndex,
) -> tuple[str | None, bool, tuple[str, ...], str | None]:
    dialect_options_value: object = index.get("dialect_options")
    dialect_options = (
        cast(dict[str, object], dialect_options_value)
        if isinstance(dialect_options_value, dict)
        else {}
    )
    return (
        _optional_string(index.get("name")),
        index["unique"],
        _reflected_index_columns(index),
        check_constraint_contract(dialect_options.get("postgresql_where")),
    )


def _index_expression_contract(expression: object) -> str:
    name = getattr(expression, "name", None)
    if isinstance(name, str):
        return name
    return (sql_contract(expression) or "").replace(" ", "")


def _reflected_index_columns(index: ReflectedIndex) -> tuple[str, ...]:
    column_names = index["column_names"]
    column_sorting_value: object = index.get("column_sorting")
    column_sorting = (
        cast(dict[str, tuple[object, ...]], column_sorting_value)
        if isinstance(column_sorting_value, dict)
        else {}
    )
    columns: list[str] = []
    for column_name in column_names:
        name = str(column_name)
        sorting = column_sorting.get(name)
        if isinstance(sorting, tuple) and any(
            isinstance(item, str) and item.lower() == "desc" for item in sorting
        ):
            name = f"{name}desc"
        columns.append(name)
    return tuple(columns)


def _optional_string(value: object | None) -> str | None:
    return value if isinstance(value, str) else None


def _optional_bool(value: object | None) -> bool | None:
    return value if isinstance(value, bool) else None


def _initially_contract(value: object | None) -> str | None:
    return value.upper() if isinstance(value, str) else None
