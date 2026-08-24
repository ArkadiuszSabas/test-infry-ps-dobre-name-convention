"""Split local credentials from DocMind users.

Revision ID: 20260521_0004
Revises: 20260521_0003
Create Date: 2026-05-21 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "20260521_0004"
down_revision: str | None = "20260521_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DOWNGRADE_BLOCKED_MESSAGE = (
    "Downgrade 20260521_0004 is not supported while external identity state exists. "
    "Remove Entra identity links, external role assignments, external browser sessions, "
    "and ensure every user has local credentials before downgrading."
)


def upgrade() -> None:
    """Move local credentials and roles out of the DocMind users table."""

    op.create_table(
        "local_credentials",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("login", sa.String(length=320), nullable=False),
        sa.Column("password_hash_algorithm", sa.String(length=64), nullable=False),
        sa.Column(
            "password_hash_parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("password_hash_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_local_credentials_updated_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_local_credentials_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_local_credentials")),
        sa.UniqueConstraint("login", name=op.f("uq_local_credentials_login")),
    )
    op.create_table(
        "identity_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("issuer", sa.String(length=512), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "provider in ('entra_id')",
            name=op.f("ck_identity_links_provider_supported"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_identity_links_updated_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_identity_links_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_identity_links")),
        sa.UniqueConstraint("user_id", "id", name=op.f("uq_identity_links_user_id")),
        sa.UniqueConstraint(
            "provider",
            "issuer",
            "tenant_id",
            "subject",
            name=op.f("uq_identity_links_provider"),
        ),
    )
    op.create_table(
        "role_assignments",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("source_provider", sa.String(length=32), nullable=False),
        sa.Column("identity_link_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role in ('admin', 'reviewer', 'operator', 'viewer')",
            name=op.f("ck_role_assignments_role_supported"),
        ),
        sa.CheckConstraint(
            "source_provider in ('local', 'entra_id')",
            name=op.f("ck_role_assignments_source_provider_supported"),
        ),
        sa.CheckConstraint(
            "(source_provider = 'local' and identity_link_id is null) "
            "or (source_provider <> 'local' and identity_link_id is not null)",
            name=op.f("ck_role_assignments_identity_link_required_for_external_provider"),
        ),
        sa.CheckConstraint(
            "created_at <= updated_at",
            name=op.f("ck_role_assignments_updated_at_not_before_created_at"),
        ),
        sa.ForeignKeyConstraint(
            ["identity_link_id"],
            ["identity_links.id"],
            name=op.f("fk_role_assignments_identity_link_id_identity_links"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_role_assignments_user_id_users"),
        ),
        sa.PrimaryKeyConstraint(
            "user_id",
            "role",
            "source_provider",
            name=op.f("pk_role_assignments"),
        ),
    )

    op.execute(
        """
        insert into local_credentials (
            user_id,
            login,
            password_hash_algorithm,
            password_hash_parameters,
            password_hash_value,
            created_at,
            updated_at
        )
        select
            id,
            login,
            password_hash_algorithm,
            password_hash_parameters,
            password_hash_value,
            created_at,
            updated_at
        from users
        """,
    )
    op.execute(
        """
        insert into role_assignments (
            user_id,
            role,
            source_provider,
            identity_link_id,
            created_at,
            updated_at
        )
        select
            users.id,
            role_value.value,
            'local',
            null,
            users.created_at,
            users.updated_at
        from users
        cross join lateral jsonb_array_elements_text(users.roles) as role_value(value)
        """,
    )

    op.create_foreign_key(
        op.f("fk_user_sessions_user_id_identity_links"),
        "user_sessions",
        "identity_links",
        ["user_id", "identity_link_id"],
        ["user_id", "id"],
    )

    op.drop_constraint(op.f("uq_users_login"), "users", type_="unique")
    op.drop_column("users", "password_hash_value")
    op.drop_column("users", "password_hash_parameters")
    op.drop_column("users", "password_hash_algorithm")
    op.drop_column("users", "roles")
    op.drop_column("users", "login")


def downgrade() -> None:
    """Move local credentials and roles back into the users table."""

    _guard_supported_downgrade_identity_state(op.get_bind())

    op.add_column("users", sa.Column("login", sa.String(length=320), nullable=True))
    op.add_column(
        "users",
        sa.Column("roles", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("password_hash_algorithm", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_hash_parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column("users", sa.Column("password_hash_value", sa.Text(), nullable=True))

    op.execute(
        """
        update users
        set
            login = local_credentials.login,
            password_hash_algorithm = local_credentials.password_hash_algorithm,
            password_hash_parameters = local_credentials.password_hash_parameters,
            password_hash_value = local_credentials.password_hash_value
        from local_credentials
        where local_credentials.user_id = users.id
        """,
    )
    op.execute(
        """
        update users
        set roles = assigned_roles.roles
        from (
            select
                user_id,
                jsonb_agg(role order by role) as roles
            from role_assignments
            where source_provider = 'local'
            group by user_id
        ) as assigned_roles
        where assigned_roles.user_id = users.id
        """,
    )
    op.alter_column("users", "login", nullable=False)
    op.alter_column("users", "roles", nullable=False)
    op.alter_column("users", "password_hash_algorithm", nullable=False)
    op.alter_column("users", "password_hash_parameters", nullable=False)
    op.alter_column("users", "password_hash_value", nullable=False)
    op.create_unique_constraint(op.f("uq_users_login"), "users", ["login"])

    op.drop_constraint(
        op.f("fk_user_sessions_user_id_identity_links"),
        "user_sessions",
        type_="foreignkey",
    )
    op.drop_table("role_assignments")
    op.drop_table("identity_links")
    op.drop_table("local_credentials")


def _guard_supported_downgrade_identity_state(connection: Connection) -> None:
    """Fail before mutating schema when legacy users cannot represent current auth state."""

    if connection.scalar(sa.text("select exists (select 1 from identity_links)")):
        raise RuntimeError(_DOWNGRADE_BLOCKED_MESSAGE)

    if connection.scalar(
        sa.text(
            """
            select exists (
                select 1
                from role_assignments
                where source_provider <> 'local'
            )
            """,
        ),
    ):
        raise RuntimeError(_DOWNGRADE_BLOCKED_MESSAGE)

    if connection.scalar(
        sa.text(
            """
            select exists (
                select 1
                from user_sessions
                where auth_provider <> 'local'
            )
            """,
        ),
    ):
        raise RuntimeError(_DOWNGRADE_BLOCKED_MESSAGE)

    if connection.scalar(
        sa.text(
            """
            select exists (
                select 1
                from users
                left join local_credentials
                    on local_credentials.user_id = users.id
                where local_credentials.user_id is null
            )
            """,
        ),
    ):
        raise RuntimeError(_DOWNGRADE_BLOCKED_MESSAGE)
