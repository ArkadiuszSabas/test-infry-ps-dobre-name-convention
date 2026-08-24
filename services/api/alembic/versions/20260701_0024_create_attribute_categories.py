"""Create system attribute categories.

Revision ID: 20260701_0024
Revises: 20260701_0023
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from re import sub
from unicodedata import category as unicode_category
from unicodedata import normalize
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260701_0024"
down_revision: str | None = "20260701_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ATTRIBUTE_CATEGORY_IS_METADATA_FLAG = "isMetadata"
DEFAULT_CATEGORY_EXTERNAL_ID = "bez_kategorii"
TIMESTAMP = datetime(2026, 7, 1, tzinfo=UTC)


def upgrade() -> None:
    """Create system attribute categories and bind attributes to them."""

    op.create_table(
        "attribute_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(external_id)) > 0", name="external_id_not_empty"),
        sa.CheckConstraint("length(trim(label)) > 0", name="label_not_empty"),
        sa.CheckConstraint("jsonb_typeof(flags) = 'object'", name="flags_object"),
        sa.CheckConstraint("status in ('active', 'inactive')", name="status_supported"),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name="updated_at_not_before_created_at",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_attribute_categories_external_id",
        "attribute_categories",
        ["external_id"],
        unique=True,
    )
    op.create_index("ix_attribute_categories_status", "attribute_categories", ["status"])
    op.add_column(
        "attribute_definitions",
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    connection = op.get_bind()
    _seed_attribute_categories(connection)
    _backfill_uncategorized_attributes(connection)
    op.alter_column("attribute_definitions", "category_id", nullable=False)

    op.create_foreign_key(
        op.f("fk_attribute_definitions_category_id_attribute_categories"),
        "attribute_definitions",
        "attribute_categories",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_attribute_definitions_category_id",
        "attribute_definitions",
        ["category_id"],
    )
    op.drop_index(op.f("ix_attribute_definitions_category"), table_name="attribute_definitions")
    op.drop_constraint(
        op.f("ck_attribute_definitions_category_not_empty"),
        "attribute_definitions",
        type_="check",
    )
    op.drop_column("attribute_definitions", "category")


def downgrade() -> None:
    """Remove system attribute categories."""

    _guard_safe_attribute_category_downgrade(op.get_bind())

    op.add_column(
        "attribute_definitions",
        sa.Column("category", sa.String(length=120), nullable=True),
    )
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            update attribute_definitions
            set category = attribute_categories.label
            from attribute_categories
            where attribute_definitions.category_id = attribute_categories.id
            """,
        ),
    )
    op.alter_column("attribute_definitions", "category", nullable=False)
    op.create_check_constraint(
        op.f("ck_attribute_definitions_category_not_empty"),
        "attribute_definitions",
        "length(trim(category)) > 0",
    )
    op.create_index(
        op.f("ix_attribute_definitions_category"),
        "attribute_definitions",
        ["category"],
    )
    op.drop_index(
        "ix_attribute_definitions_category_id",
        table_name="attribute_definitions",
    )
    op.drop_constraint(
        op.f("fk_attribute_definitions_category_id_attribute_categories"),
        "attribute_definitions",
        type_="foreignkey",
    )
    op.drop_column("attribute_definitions", "category_id")
    op.drop_index("ix_attribute_categories_status", table_name="attribute_categories")
    op.drop_index("uq_attribute_categories_external_id", table_name="attribute_categories")
    op.drop_table("attribute_categories")


def _seed_attribute_categories(connection: Connection) -> None:
    labels = _existing_category_labels(connection)
    external_ids_by_label = _category_external_ids_by_label(labels)
    seeded_categories = {DEFAULT_CATEGORY_EXTERNAL_ID: "Bez kategorii"}
    dynamic_categories: dict[str, tuple[str, bool]] = {}
    for label in labels:
        external_id = external_ids_by_label[label]
        dynamic_categories.setdefault(external_id, (label, _is_metadata_seed_label(label)))

    categories = {external_id: (label, False) for external_id, label in seeded_categories.items()}
    for external_id, category in dynamic_categories.items():
        categories.setdefault(external_id, category)

    for external_id, category in categories.items():
        label, is_metadata = category
        _upsert_attribute_category(
            connection,
            external_id=external_id,
            label=label,
            is_metadata=is_metadata,
        )

    for label in labels:
        connection.execute(
            sa.text(
                """
                update attribute_definitions
                set category_id = (
                    select id
                    from attribute_categories
                    where external_id = :category_external_id
                )
                where category = :category
                """,
            ),
            {
                "category_external_id": external_ids_by_label[label],
                "category": label,
            },
        )


def _backfill_uncategorized_attributes(connection: Connection) -> None:
    connection.execute(
        sa.text(
            """
            update attribute_definitions
            set category_id = (
                select id
                from attribute_categories
                where external_id = :default_category_external_id
            )
            where category_id is null
            """,
        ),
        {"default_category_external_id": DEFAULT_CATEGORY_EXTERNAL_ID},
    )


def _upsert_attribute_category(
    connection: Connection,
    *,
    external_id: str,
    label: str,
    is_metadata: bool,
) -> None:
    connection.execute(
        sa.text(
            """
            insert into attribute_categories (
                id,
                external_id,
                label,
                flags,
                status,
                created_at,
                updated_at
            )
            values (
                :id,
                :external_id,
                :label,
                jsonb_build_object(
                    cast(:flag_external_id as text),
                    cast(:is_metadata as boolean)
                ),
                'active',
                :timestamp,
                :timestamp
            )
            on conflict (external_id) do update
            set label = excluded.label,
                flags = attribute_categories.flags || excluded.flags,
                status = 'active',
                updated_at = excluded.updated_at
            """,
        ),
        {
            "id": str(_category_id(external_id)),
            "external_id": external_id,
            "label": label,
            "flag_external_id": ATTRIBUTE_CATEGORY_IS_METADATA_FLAG,
            "is_metadata": is_metadata,
            "timestamp": TIMESTAMP,
        },
    )


def _existing_category_labels(connection: Connection) -> tuple[str, ...]:
    return tuple(
        row.category
        for row in connection.execute(
            sa.text(
                """
                select distinct trim(category) as category
                from attribute_definitions
                where category is not null
                  and length(trim(category)) > 0
                order by trim(category)
                """,
            ),
        )
    )


def _category_external_ids_by_label(labels: tuple[str, ...]) -> dict[str, str]:
    base_external_ids = {label: _category_external_id(label) for label in labels}
    base_counts: dict[str, int] = {}
    for external_id in base_external_ids.values():
        base_counts[external_id] = base_counts.get(external_id, 0) + 1

    assigned_external_ids = {DEFAULT_CATEGORY_EXTERNAL_ID}
    external_ids_by_label: dict[str, str] = {}
    for label in labels:
        external_id = base_external_ids[label]
        is_default_label = label.casefold() == "bez kategorii"
        if is_default_label:
            external_ids_by_label[label] = DEFAULT_CATEGORY_EXTERNAL_ID
            continue

        if base_counts[external_id] == 1 and external_id not in assigned_external_ids:
            external_ids_by_label[label] = external_id
            assigned_external_ids.add(external_id)
            continue

        disambiguated_external_id = _disambiguated_category_external_id(
            external_id,
            label,
        )
        assigned_external_ids.add(disambiguated_external_id)
        external_ids_by_label[label] = disambiguated_external_id

    return external_ids_by_label


def _disambiguated_category_external_id(base_external_id: str, label: str) -> str:
    prefix = base_external_id[:63].rstrip("_") or "category"
    return f"{prefix}_{_category_id(label).hex[:16]}"


def _category_external_id(label: str) -> str:
    if label.casefold() == "bez kategorii":
        return DEFAULT_CATEGORY_EXTERNAL_ID

    ascii_label = "".join(
        character for character in normalize("NFKD", label) if unicode_category(character) != "Mn"
    )
    normalized = sub(r"[^a-z0-9]+", "_", ascii_label.casefold()).strip("_")
    if not normalized:
        return "category_" + _category_id(label).hex[:16]
    if len(normalized) <= 80:
        return normalized
    return normalized[:63].rstrip("_") + "_" + _category_id(label).hex[:16]


def _category_id(external_id: str):
    return uuid5(NAMESPACE_URL, f"docmind:attribute-category:{external_id}")


def _is_metadata_seed_label(label: str) -> bool:
    return label.casefold() in {"metadata", "metadane"}


def _guard_safe_attribute_category_downgrade(connection: Connection) -> None:
    changed_category_count = int(
        connection.scalar(
            sa.text(
                """
                select count(*)
                from attribute_categories
                where created_at <> :timestamp
                   or updated_at <> :timestamp
                """,
            ),
            {"timestamp": TIMESTAMP},
        )
        or 0,
    )
    if changed_category_count:
        raise RuntimeError(
            "Cannot downgrade attribute categories after category entries or flags were changed.",
        )
