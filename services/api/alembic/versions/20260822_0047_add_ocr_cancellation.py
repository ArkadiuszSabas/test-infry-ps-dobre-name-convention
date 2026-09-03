"""Add OCR run cancellation state and fencing.

Revision ID: 20260822_0047
Revises: 20260822_0046
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0047"
down_revision: str | Sequence[str] | None = "20260822_0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "drop trigger if exists trg_ocr_pipeline_runs_legacy_write_guard on ocr_pipeline_runs"
    )
    op.execute("drop function if exists guard_legacy_ocr_pipeline_run_write()")

    op.add_column(
        "ocr_pipeline_runs",
        sa.Column("cancellation_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ocr_pipeline_runs",
        sa.Column("cancellation_requested_by_actor_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "ocr_pipeline_runs",
        sa.Column("cancellation_requested_by_actor_login", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "ocr_pipeline_run_attempts",
        sa.Column("cancellation_deadline_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.drop_index("uq_ocr_pipeline_runs_active_document_id", table_name="ocr_pipeline_runs")
    op.drop_constraint(
        op.f("ck_ocr_pipeline_runs_status_supported"), "ocr_pipeline_runs", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_runs_status_supported"),
        "ocr_pipeline_runs",
        "status in ('pending', 'running', 'cancelling', 'succeeded', "
        "'partial_failed', 'failed', 'cancelled')",
    )
    op.create_index(
        "uq_ocr_pipeline_runs_active_document_id",
        "ocr_pipeline_runs",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("status in ('pending', 'running', 'cancelling')"),
    )

    op.drop_constraint(
        op.f("ck_ocr_pipeline_run_attempts_status_supported"),
        "ocr_pipeline_run_attempts",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_run_attempts_status_supported"),
        "ocr_pipeline_run_attempts",
        "status in ('reserved', 'running', 'succeeded', 'partial_failed', "
        "'failed', 'cancelled', 'indeterminate', 'lost')",
    )


def downgrade() -> None:
    connection = op.get_bind()
    active_cancellations = int(
        connection.scalar(
            sa.text(
                "select count(*) from ocr_pipeline_runs where status in ('cancelling', 'cancelled')"
            )
        )
        or 0
    )
    if active_cancellations:
        raise RuntimeError("Cannot downgrade while OCR cancellation history exists.")
    op.drop_constraint(
        op.f("ck_ocr_pipeline_run_attempts_status_supported"),
        "ocr_pipeline_run_attempts",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_run_attempts_status_supported"),
        "ocr_pipeline_run_attempts",
        "status in ('reserved', 'running', 'succeeded', 'partial_failed', "
        "'failed', 'indeterminate', 'lost')",
    )
    op.drop_index("uq_ocr_pipeline_runs_active_document_id", table_name="ocr_pipeline_runs")
    op.drop_constraint(
        op.f("ck_ocr_pipeline_runs_status_supported"), "ocr_pipeline_runs", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_ocr_pipeline_runs_status_supported"),
        "ocr_pipeline_runs",
        "status in ('pending', 'running', 'succeeded', 'partial_failed', 'failed')",
    )
    op.create_index(
        "uq_ocr_pipeline_runs_active_document_id",
        "ocr_pipeline_runs",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("status in ('pending', 'running')"),
    )
    op.drop_column("ocr_pipeline_run_attempts", "cancellation_deadline_at")
    op.drop_column("ocr_pipeline_runs", "cancellation_requested_by_actor_login")
    op.drop_column("ocr_pipeline_runs", "cancellation_requested_by_actor_id")
    op.drop_column("ocr_pipeline_runs", "cancellation_requested_at")
    op.execute(_LEGACY_WRITE_GUARD_FUNCTION)
    op.execute(
        """
        create trigger trg_ocr_pipeline_runs_legacy_write_guard
        before update on ocr_pipeline_runs
        for each row execute function guard_legacy_ocr_pipeline_run_write()
        """
    )


_LEGACY_WRITE_GUARD_FUNCTION = """
create function guard_legacy_ocr_pipeline_run_write()
returns trigger
language plpgsql
as $$
declare
    latest_attempt ocr_pipeline_run_attempts%rowtype;
    observed_at timestamptz := clock_timestamp();
    started_at timestamptz;
begin
    if old.status = 'failed' and new.status = 'running' then
        select * into latest_attempt
        from ocr_pipeline_run_attempts
        where run_id = old.id
        order by attempt_number desc
        limit 1
        for update;

        if found
           and latest_attempt.status = 'running'
           and latest_attempt.attempt_number >= 1 then
            return new;
        end if;

        raise exception 'Unfenced OCR pipeline retry rejected'
            using errcode = '55000';
    end if;

    if old.status = 'running'
       and new.status = 'running'
       and new is distinct from old then
        select * into latest_attempt
        from ocr_pipeline_run_attempts
        where run_id = old.id
        order by attempt_number desc
        limit 1
        for update;

        if found
           and latest_attempt.status = 'running'
           and new.updated_at = latest_attempt.started_at
           and new.metrics ->> 'execution_attempt_count'
               = latest_attempt.attempt_number::text then
            return new;
        end if;

        raise exception 'Unfenced OCR pipeline running write rejected'
            using errcode = '55000';
    end if;

    if old.status in ('succeeded', 'partial_failed', 'failed')
       and new is distinct from old then
        raise exception 'Terminal OCR pipeline run is immutable during rolling deployment'
            using errcode = '55000';
    end if;

    if old.status = 'pending' and new.status = 'running' then
        if not exists (
            select 1 from ocr_pipeline_run_attempts where run_id = old.id
        ) then
            started_at := least(coalesce(new.started_at, observed_at), observed_at);
            insert into ocr_pipeline_run_attempts (
                attempt_id,
                run_id,
                owner_token,
                attempt_number,
                fencing_token,
                status,
                started_at,
                invocation_started_at,
                last_renewed_at,
                lease_expires_at
            )
            values (
                gen_random_uuid(),
                old.id,
                gen_random_uuid(),
                1,
                1,
                'running',
                started_at,
                started_at,
                observed_at,
                observed_at + interval '30 minutes'
            );
        end if;
        return new;
    end if;

    if old.status = 'running'
       and new.status in ('succeeded', 'partial_failed', 'failed') then
        select * into latest_attempt
        from ocr_pipeline_run_attempts
        where run_id = old.id
        order by attempt_number desc
        limit 1
        for update;

        if not found then
            raise exception 'OCR pipeline terminal write has no execution attempt'
                using errcode = '55000';
        end if;

        if latest_attempt.status = new.status
           and latest_attempt.completed_at = new.completed_at then
            return new;
        end if;

        if latest_attempt.status = 'lost'
           and new.status = 'failed'
           and new.error ->> 'code' = 'OCR_PIPELINE_RUN_ATTEMPTS_EXHAUSTED' then
            return new;
        end if;

        if latest_attempt.status <> 'running'
           or latest_attempt.attempt_number <> 1
           or latest_attempt.lease_expires_at <= observed_at then
            raise exception 'Stale OCR pipeline terminal write rejected'
                using errcode = '55000';
        end if;

        update ocr_pipeline_run_attempts
        set status = new.status,
            completed_at = coalesce(new.completed_at, observed_at),
            error_code = new.error ->> 'code'
        where attempt_id = latest_attempt.attempt_id;
    end if;

    return new;
end;
$$
"""
