"""Add durable OCR run observability identity and connector context.

Revision ID: 20260818_0043
Revises: 20260806_0042
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260818_0043"
down_revision: str | Sequence[str] | None = "20260806_0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "ocr_pipeline_runs"
_LEGACY_WRITE_GUARD_TRIGGER = "trg_ocr_pipeline_runs_legacy_write_guard"


def upgrade() -> None:
    op.add_column(
        _TABLE_NAME,
        sa.Column(
            "started_by_actor_type",
            sa.String(length=16),
            nullable=False,
            server_default="system",
        ),
    )
    op.add_column(
        _TABLE_NAME,
        sa.Column("started_by_actor_login", sa.String(length=320), nullable=True),
    )
    for column_name in (
        "document_source",
        "document_connector",
        "connector_instance_id",
        "connector_display_name",
        "connector_correlation_id",
    ):
        op.add_column(
            _TABLE_NAME,
            sa.Column(column_name, sa.String(length=200), nullable=True),
        )

    # The rolling-deployment guard intentionally rejects every update to terminal
    # runs (and unfenced updates to running runs). The backfill only writes the new
    # snapshot columns, so suspend the named guard inside this transactional
    # migration and restore it before committing.
    op.execute(f"alter table {_TABLE_NAME} disable trigger {_LEGACY_WRITE_GUARD_TRIGGER}")
    op.execute(
        sa.text(
            """
            UPDATE ocr_pipeline_runs AS run
            SET document_source = document.source,
                document_connector = document.connector,
                connector_instance_id = document.connector_instance_id,
                connector_display_name = document.connector,
                connector_correlation_id = document.connector_correlation_id,
                started_by_actor_type = CASE
                    WHEN run.started_by_actor_id LIKE 'connector:%' THEN 'connector'
                    WHEN run.started_by_actor_id IS NOT NULL THEN 'human'
                    ELSE 'system'
                END
            FROM documents AS document
            WHERE document.id = run.document_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE ocr_pipeline_runs AS run
            SET started_by_actor_login = NULLIF(BTRIM(credentials.login), '')
            FROM local_credentials AS credentials
            WHERE run.started_by_actor_type = 'human'
              AND run.started_by_actor_id = credentials.user_id::text
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE ocr_pipeline_runs AS run
            SET started_by_actor_login = NULLIF(BTRIM(identity.email), '')
            FROM (
                SELECT DISTINCT ON (user_id) user_id, email
                FROM identity_links
                WHERE email IS NOT NULL
                ORDER BY user_id, created_at ASC, id ASC
            ) AS identity
            WHERE run.started_by_actor_type = 'human'
              AND run.started_by_actor_login IS NULL
              AND run.started_by_actor_id = identity.user_id::text
            """
        )
    )
    op.execute(f"alter table {_TABLE_NAME} enable trigger {_LEGACY_WRITE_GUARD_TRIGGER}")

    op.create_check_constraint(
        op.f("ck_ocr_pipeline_runs_started_by_actor_type_supported"),
        _TABLE_NAME,
        "started_by_actor_type in ('human', 'connector', 'system')",
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_runs_started_by_actor_login_not_empty"),
        _TABLE_NAME,
        "started_by_actor_login is null or length(trim(started_by_actor_login)) > 0",
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_runs_started_by_actor_login_human_only"),
        _TABLE_NAME,
        "started_by_actor_type = 'human' or started_by_actor_login is null",
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_runs_started_by_actor_identity_valid"),
        _TABLE_NAME,
        "(started_by_actor_type = 'human' and started_by_actor_id is not null) "
        "or (started_by_actor_type = 'connector' "
        "and started_by_actor_id like 'connector:%') "
        "or started_by_actor_type = 'system'",
    )
    op.alter_column(_TABLE_NAME, "started_by_actor_type", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_ocr_pipeline_runs_started_by_actor_identity_valid"),
        _TABLE_NAME,
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_ocr_pipeline_runs_started_by_actor_login_human_only"),
        _TABLE_NAME,
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_ocr_pipeline_runs_started_by_actor_login_not_empty"),
        _TABLE_NAME,
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_ocr_pipeline_runs_started_by_actor_type_supported"),
        _TABLE_NAME,
        type_="check",
    )
    for column_name in (
        "connector_correlation_id",
        "connector_display_name",
        "connector_instance_id",
        "document_connector",
        "document_source",
        "started_by_actor_login",
        "started_by_actor_type",
    ):
        op.drop_column(_TABLE_NAME, column_name)
