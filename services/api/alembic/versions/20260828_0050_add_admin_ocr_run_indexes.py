"""Add bounded administrative OCR run list indexes.

Revision ID: 20260828_0050
Revises: 20260828_0049
"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection, RowMapping

revision: str = "20260828_0050"
down_revision: str | Sequence[str] | None = "20260828_0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE_INDEX_NAME = "ix_ocr_pipeline_runs_admin_active_updated"
_HISTORY_INDEX_NAME = "ix_ocr_pipeline_runs_admin_history_completed"
_EXPECTED_INDEX_NAMES = frozenset({_ACTIVE_INDEX_NAME, _HISTORY_INDEX_NAME})
_EXPECTED_INDEX_KEYS = {
    _ACTIVE_INDEX_NAME: ("updated_at", "id"),
    _HISTORY_INDEX_NAME: ("completed_at", "id"),
}
_EXPECTED_INDEX_KEY_OPTIONS = {
    _ACTIVE_INDEX_NAME: (0, 0),
    _HISTORY_INDEX_NAME: (3, 3),
}
_EXPECTED_NORMALIZED_PREDICATES = {
    _ACTIVE_INDEX_NAME: "status=anyarray['pending','running','cancelling']",
    _HISTORY_INDEX_NAME: ("status=anyarray['succeeded','partial_failed','failed','cancelled']"),
}
_POSTGRES_TEXT_CAST_PATTERN = re.compile(
    r"::(?:character varying|varchar|text)(?:\(\d+\))?(?:\[\])?",
)


def upgrade() -> None:
    connection = op.get_bind()
    hydration_column_exists = _hydration_column_exists(connection)
    existing_indexes = _load_admin_index_fingerprints(connection)

    if hydration_column_exists:
        if existing_indexes:
            raise RuntimeError(
                "Revision 20260828_0050 found admin OCR run indexes before the canonical "
                "upgrade, but document_review_versions.pipeline_sources_hydrated already "
                "exists. Refusing to guess whether the schema was partially repaired.",
            )
        _create_admin_indexes()
        return

    _require_legacy_branch_indexes(connection, existing_indexes)
    _add_hydration_cache_column()


def _create_admin_indexes() -> None:
    op.create_index(
        _ACTIVE_INDEX_NAME,
        "ocr_pipeline_runs",
        ["updated_at", "id"],
        unique=False,
        postgresql_where=sa.text("status in ('pending', 'running', 'cancelling')"),
    )
    op.create_index(
        _HISTORY_INDEX_NAME,
        "ocr_pipeline_runs",
        [sa.text("completed_at desc"), sa.text("id desc")],
        unique=False,
        postgresql_where=sa.text(
            "status in ('succeeded', 'partial_failed', 'failed', 'cancelled')"
        ),
    )


def _hydration_column_exists(connection: Connection) -> bool:
    return bool(
        connection.execute(
            sa.text(
                """
                select exists (
                    select 1
                    from information_schema.columns
                    where table_schema = current_schema()
                      and table_name = 'document_review_versions'
                      and column_name = 'pipeline_sources_hydrated'
                )
                """,
            ),
        ).scalar_one(),
    )


def _load_admin_index_fingerprints(connection: Connection) -> dict[str, RowMapping]:
    rows = connection.execute(
        sa.text(
            """
            select
                index_relation.relname as index_name,
                access_method.amname as access_method,
                index_catalog.indisunique as is_unique,
                index_catalog.indisvalid as is_valid,
                index_catalog.indisready as is_ready,
                array(
                    select pg_get_indexdef(
                        index_catalog.indexrelid,
                        key_ordinal,
                        true
                    )
                    from generate_series(
                        1,
                        index_catalog.indnkeyatts::integer
                    ) as key_ordinal
                    order by key_ordinal
                ) as key_definitions,
                array(
                    select index_catalog.indoption[key_ordinal - 1]
                    from generate_series(
                        1,
                        index_catalog.indnkeyatts::integer
                    ) as key_ordinal
                    order by key_ordinal
                ) as key_options,
                pg_get_expr(
                    index_catalog.indpred,
                    index_catalog.indrelid,
                    true
                ) as predicate
            from pg_index as index_catalog
            join pg_class as index_relation
              on index_relation.oid = index_catalog.indexrelid
            join pg_class as table_relation
              on table_relation.oid = index_catalog.indrelid
            join pg_namespace as table_namespace
              on table_namespace.oid = table_relation.relnamespace
            join pg_am as access_method
              on access_method.oid = index_relation.relam
            where table_namespace.nspname = current_schema()
              and table_relation.relname = 'ocr_pipeline_runs'
              and index_relation.relname in (
                  'ix_ocr_pipeline_runs_admin_active_updated',
                  'ix_ocr_pipeline_runs_admin_history_completed'
              )
            """,
        ),
    ).mappings()
    return {str(row["index_name"]): row for row in rows}


def _require_legacy_branch_indexes(
    connection: Connection,
    indexes: dict[str, RowMapping],
) -> None:
    if frozenset(indexes) != _EXPECTED_INDEX_NAMES:
        found = ", ".join(sorted(indexes)) or "none"
        raise RuntimeError(
            "Revision 20260828_0050 cannot reconcile the legacy branch revision "
            f"20260828_0049 because its admin OCR run indexes do not match the expected set. "
            f"Found: {found}.",
        )

    for index_name in sorted(_EXPECTED_INDEX_NAMES):
        fingerprint = indexes[index_name]
        actual_keys = tuple(
            " ".join(str(key).lower().split()) for key in fingerprint["key_definitions"]
        )
        if actual_keys != _EXPECTED_INDEX_KEYS[index_name]:
            raise RuntimeError(
                "Revision 20260828_0050 cannot reconcile legacy index "
                f"{index_name}: unexpected key definition {actual_keys}.",
            )
        actual_key_options = tuple(int(option) for option in fingerprint["key_options"])
        if actual_key_options != _EXPECTED_INDEX_KEY_OPTIONS[index_name]:
            raise RuntimeError(
                "Revision 20260828_0050 cannot reconcile legacy index "
                f"{index_name}: unexpected sort or null-order options "
                f"{actual_key_options}.",
            )
        if (
            str(fingerprint["access_method"]).lower() != "btree"
            or bool(fingerprint["is_unique"])
            or not bool(fingerprint["is_valid"])
            or not bool(fingerprint["is_ready"])
        ):
            raise RuntimeError(
                "Revision 20260828_0050 cannot reconcile legacy index "
                f"{index_name}: expected a valid, ready, non-unique btree index.",
            )

        predicate = fingerprint["predicate"]
        if not isinstance(predicate, str) or not predicate.strip():
            raise RuntimeError(
                "Revision 20260828_0050 cannot reconcile legacy index "
                f"{index_name}: expected a partial-index predicate.",
            )
        _require_expected_predicate(index_name, predicate)


def _require_expected_predicate(
    index_name: str,
    predicate: str,
) -> None:
    normalized = predicate.lower().replace('"', "")
    normalized = _POSTGRES_TEXT_CAST_PATTERN.sub("", normalized)
    normalized = re.sub(r"[\s()]", "", normalized)
    if normalized != _EXPECTED_NORMALIZED_PREDICATES[index_name]:
        raise RuntimeError(
            "Revision 20260828_0050 cannot reconcile legacy index "
            f"{index_name}: unexpected partial-index predicate.",
        )


def _add_hydration_cache_column() -> None:
    op.add_column(
        "document_review_versions",
        sa.Column(
            "pipeline_sources_hydrated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_index(_HISTORY_INDEX_NAME, table_name="ocr_pipeline_runs")
    op.drop_index(_ACTIVE_INDEX_NAME, table_name="ocr_pipeline_runs")
