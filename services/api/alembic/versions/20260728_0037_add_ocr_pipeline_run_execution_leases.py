"""Add fenced OCR pipeline execution attempts and leases.

Revision ID: 20260728_0037
Revises: 20260728_0036
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "20260728_0037"
down_revision: str | Sequence[str] | None = "20260728_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ocr_pipeline_run_attempts",
        sa.Column("attempt_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("owner_token", sa.UUID(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("fencing_token", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invocation_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_renewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.CheckConstraint(
            "attempt_number > 0",
            name=op.f("ck_ocr_pipeline_run_attempts_attempt_number_positive"),
        ),
        sa.CheckConstraint(
            "fencing_token > 0",
            name=op.f("ck_ocr_pipeline_run_attempts_fencing_token_positive"),
        ),
        sa.CheckConstraint(
            "status in "
            "('running', 'succeeded', 'partial_failed', 'failed', 'indeterminate', 'lost')",
            name=op.f("ck_ocr_pipeline_run_attempts_status_supported"),
        ),
        sa.CheckConstraint(
            "started_at <= last_renewed_at",
            name=op.f("ck_ocr_pipeline_run_attempts_renewed_at_not_before_started_at"),
        ),
        sa.CheckConstraint(
            "invocation_started_at is null or started_at <= invocation_started_at",
            name=op.f("ck_ocr_pipeline_run_attempts_invocation_not_before_started_at"),
        ),
        sa.CheckConstraint(
            "last_renewed_at < lease_expires_at",
            name=op.f("ck_ocr_pipeline_run_attempts_lease_expires_after_renewal"),
        ),
        sa.CheckConstraint(
            "completed_at is null or started_at <= completed_at",
            name=op.f("ck_ocr_pipeline_run_attempts_completed_at_not_before_started_at"),
        ),
        sa.CheckConstraint(
            "(status = 'running' and completed_at is null) "
            "or (status <> 'running' and completed_at is not null)",
            name=op.f("ck_ocr_pipeline_run_attempts_completion_matches_status"),
        ),
        sa.CheckConstraint(
            "error_code is null or length(trim(error_code)) > 0",
            name=op.f("ck_ocr_pipeline_run_attempts_error_code_not_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["ocr_pipeline_runs.id"],
            name=op.f("fk_ocr_pipeline_run_attempts_run_id_ocr_pipeline_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "attempt_id",
            name=op.f("pk_ocr_pipeline_run_attempts"),
        ),
    )
    op.create_index(
        "ix_ocr_pipeline_run_attempts_run_id",
        "ocr_pipeline_run_attempts",
        ["run_id"],
    )
    op.create_index(
        "uq_ocr_pipeline_run_attempts_run_attempt_number",
        "ocr_pipeline_run_attempts",
        ["run_id", "attempt_number"],
        unique=True,
    )
    op.create_index(
        "uq_ocr_pipeline_run_attempts_run_fencing_token",
        "ocr_pipeline_run_attempts",
        ["run_id", "fencing_token"],
        unique=True,
    )
    op.create_index(
        "uq_ocr_pipeline_run_attempts_active_run_id",
        "ocr_pipeline_run_attempts",
        ["run_id"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
    )
    op.create_index(
        "ix_ocr_pipeline_run_attempts_lease_expires_at",
        "ocr_pipeline_run_attempts",
        ["lease_expires_at"],
    )
    op.execute(_LEGACY_WRITE_GUARD_FUNCTION)
    op.execute(
        """
        create trigger trg_ocr_pipeline_runs_legacy_write_guard
        before update on ocr_pipeline_runs
        for each row execute function guard_legacy_ocr_pipeline_run_write()
        """
    )
    op.execute(
        """
        with observed as materialized (
            select clock_timestamp() as observed_at
        )
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
        select
            gen_random_uuid(),
            id,
            gen_random_uuid(),
            1,
            1,
            'running',
            least(coalesce(started_at, observed.observed_at), observed.observed_at),
            least(coalesce(started_at, observed.observed_at), observed.observed_at),
            observed.observed_at,
            observed.observed_at + interval '30 minutes'
        from ocr_pipeline_runs
        cross join observed
        where status = 'running'
        """
    )


def downgrade() -> None:
    _guard_attempt_history_downgrade(op.get_bind())
    op.execute("drop trigger trg_ocr_pipeline_runs_legacy_write_guard on ocr_pipeline_runs")
    op.execute("drop function guard_legacy_ocr_pipeline_run_write()")
    op.drop_index(
        "ix_ocr_pipeline_run_attempts_lease_expires_at",
        table_name="ocr_pipeline_run_attempts",
    )
    op.drop_index(
        "uq_ocr_pipeline_run_attempts_active_run_id",
        table_name="ocr_pipeline_run_attempts",
    )
    op.drop_index(
        "uq_ocr_pipeline_run_attempts_run_fencing_token",
        table_name="ocr_pipeline_run_attempts",
    )
    op.drop_index(
        "uq_ocr_pipeline_run_attempts_run_attempt_number",
        table_name="ocr_pipeline_run_attempts",
    )
    op.drop_index(
        "ix_ocr_pipeline_run_attempts_run_id",
        table_name="ocr_pipeline_run_attempts",
    )
    op.drop_table("ocr_pipeline_run_attempts")


def _guard_attempt_history_downgrade(connection: Connection) -> None:
    connection.execute(
        sa.text("lock table ocr_pipeline_runs, ocr_pipeline_run_attempts in access exclusive mode")
    )
    attempt_count = int(
        connection.scalar(sa.text("select count(*) from ocr_pipeline_run_attempts")) or 0
    )
    if attempt_count:
        raise RuntimeError(
            "Cannot downgrade OCR pipeline execution leases while attempt history exists: "
            f"ocr_pipeline_run_attempts={attempt_count}."
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
        select *
        into latest_attempt
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
        select *
        into latest_attempt
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
        select *
        into latest_attempt
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
