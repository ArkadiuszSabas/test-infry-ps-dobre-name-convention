"""Allow free-form catalog external IDs.

Revision ID: 20260624_0019
Revises: 20260624_0018
Create Date: 2026-06-24 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "20260624_0019"
down_revision: str | Sequence[str] | None = "20260624_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow any non-empty catalog external ID value when one is provided."""

    op.drop_constraint(
        op.f("ck_document_types_external_id_snake_case"),
        "document_types",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_document_types_external_id_not_empty"),
        "document_types",
        "external_id is null or length(trim(external_id)) > 0",
    )

    op.drop_constraint(
        op.f("ck_attribute_definitions_external_id_snake_case"),
        "attribute_definitions",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_attribute_definitions_external_id_not_empty"),
        "attribute_definitions",
        "external_id is null or length(trim(external_id)) > 0",
    )


def downgrade() -> None:
    """Restore the previous optional snake_case catalog external ID checks."""

    _guard_snake_case_catalog_external_ids(op.get_bind())
    op.drop_constraint(
        op.f("ck_attribute_definitions_external_id_not_empty"),
        "attribute_definitions",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_attribute_definitions_external_id_snake_case"),
        "attribute_definitions",
        "external_id is null or external_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
    )

    op.drop_constraint(
        op.f("ck_document_types_external_id_not_empty"),
        "document_types",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_document_types_external_id_snake_case"),
        "document_types",
        "external_id is null or external_id ~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'",
    )


def _guard_snake_case_catalog_external_ids(connection: Any) -> None:
    """Block downgrade when upgraded data cannot satisfy old external ID checks."""

    invalid_rows: list[str] = []
    for table_name in ("attribute_definitions", "document_types"):
        row_count = int(
            connection.scalar(
                sa.text(
                    f"""
                    select count(*)
                    from {table_name}
                    where external_id is not null
                      and external_id !~ '^[a-z][a-z0-9]*(_[a-z0-9]+)*$'
                    """,
                ),
            )
            or 0,
        )
        if row_count:
            invalid_rows.append(f"{table_name}={row_count}")

    if invalid_rows:
        raise RuntimeError(
            "Cannot downgrade free-form catalog external IDs while non-snake-case "
            f"external_id values exist: {', '.join(invalid_rows)}. Normalize or remove "
            "those values before downgrading to 20260624_0018.",
        )
