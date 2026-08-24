"""User-management persistence adapters."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.auth.ports import ManagedUserRepository
from docmind_api.domain.auth.actors import AuthProvider, Role
from docmind_api.domain.auth.identity import RoleAssignment
from docmind_api.domain.auth.local_accounts import PasswordHash
from docmind_api.domain.auth.users import ManagedUser, UserStatus
from docmind_api.infrastructure.persistence.auth.actor_queries import (
    auth_providers_for_users,
)
from docmind_api.infrastructure.persistence.auth.tables import (
    identity_links_table,
    local_credentials_table,
    role_assignments_table,
    users_table,
)


class SqlAlchemyManagedUserRepository(ManagedUserRepository):
    """PostgreSQL-backed admin user-management repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_users(
        self,
        *,
        include_deleted: bool = False,
    ) -> tuple[ManagedUser, ...]:
        """Return users ordered for admin management screens."""

        statement = select(users_table).order_by(
            users_table.c.display_name.asc(),
            users_table.c.created_at.desc(),
        )
        if not include_deleted:
            statement = statement.where(users_table.c.status != UserStatus.DELETED.value)

        result = await self._session.execute(statement)
        return await _managed_users_from_rows(
            self._session,
            tuple(result.mappings()),
        )

    async def get_by_id(
        self,
        user_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None:
        """Return one user-management read model by id."""

        statement = select(users_table).where(users_table.c.id == user_id)
        if not include_deleted:
            statement = statement.where(users_table.c.status != UserStatus.DELETED.value)

        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        users = await _managed_users_from_rows(self._session, (row,))
        return users[0]

    async def update_profile(
        self,
        *,
        user_id: UUID,
        display_name: str | None,
        status: UserStatus | None,
        roles: tuple[Role, ...] | None,
        updated_at: datetime,
    ) -> ManagedUser | None:
        """Update mutable user fields and local role assignments."""

        if await self.get_by_id(user_id) is None:
            return None

        values: dict[str, Any] = {"updated_at": updated_at}
        if display_name is not None:
            values["display_name"] = display_name
        if status is not None:
            values["status"] = status.value

        await self._session.execute(
            update(users_table)
            .where(
                users_table.c.id == user_id,
                users_table.c.status != UserStatus.DELETED.value,
            )
            .values(**values),
        )

        if roles is not None:
            await _replace_local_role_assignments(
                self._session,
                user_id=user_id,
                roles=roles,
                timestamp=updated_at,
            )

        return await self.get_by_id(user_id, include_deleted=status == UserStatus.DELETED)

    async def soft_delete(
        self,
        *,
        user_id: UUID,
        deleted_at: datetime,
    ) -> ManagedUser | None:
        """Mark a user as deleted without removing audit-linked rows."""

        statement = (
            update(users_table)
            .where(
                users_table.c.id == user_id,
                users_table.c.status != UserStatus.DELETED.value,
            )
            .values(status=UserStatus.DELETED.value, updated_at=deleted_at)
            .returning(users_table.c.id)
        )
        result = await self._session.execute(statement)
        if result.scalar_one_or_none() is None:
            return None

        return await self.get_by_id(user_id, include_deleted=True)

    async def update_local_password_hash(
        self,
        *,
        user_id: UUID,
        password_hash: PasswordHash,
        updated_at: datetime,
    ) -> bool:
        """Replace a local credential password hash for an existing local user."""

        if await self.get_by_id(user_id) is None:
            return False

        statement = (
            update(local_credentials_table)
            .where(local_credentials_table.c.user_id == user_id)
            .values(
                password_hash_algorithm=password_hash.algorithm,
                password_hash_parameters=[
                    {"name": parameter.name, "value": parameter.value}
                    for parameter in password_hash.parameters
                ],
                password_hash_value=password_hash.hash_value,
                updated_at=updated_at,
            )
            .returning(local_credentials_table.c.user_id)
        )
        result = await self._session.execute(statement)
        if result.scalar_one_or_none() is None:
            return False

        await self._session.execute(
            update(users_table).where(users_table.c.id == user_id).values(updated_at=updated_at),
        )
        return True


async def _managed_users_from_rows(
    session: AsyncSession,
    rows: tuple[Mapping[Any, Any], ...],
) -> tuple[ManagedUser, ...]:
    if not rows:
        return ()

    user_ids = tuple(row["id"] for row in rows)
    roles_by_user_id = await _roles_for_users(session, user_ids)
    providers_by_user_id = await auth_providers_for_users(session, user_ids)
    emails_by_user_id = await _emails_for_users(session, user_ids)
    return tuple(
        ManagedUser(
            id=row["id"],
            display_name=row["display_name"],
            status=UserStatus(row["status"]),
            roles=roles_by_user_id.get(row["id"], ()),
            auth_providers=providers_by_user_id.get(row["id"], ()),
            email=emails_by_user_id.get(row["id"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    )


async def _roles_for_users(
    session: AsyncSession,
    user_ids: tuple[UUID, ...],
) -> dict[UUID, tuple[Role, ...]]:
    result = await session.execute(
        select(role_assignments_table.c.user_id, role_assignments_table.c.role).where(
            role_assignments_table.c.user_id.in_(user_ids),
        ),
    )
    roles_by_user_id: dict[UUID, set[Role]] = {user_id: set() for user_id in user_ids}
    for row in result:
        roles_by_user_id[row.user_id].add(Role(row.role))

    return {
        user_id: tuple(sorted(roles, key=lambda role: role.value))
        for user_id, roles in roles_by_user_id.items()
    }


async def _emails_for_users(
    session: AsyncSession,
    user_ids: tuple[UUID, ...],
) -> dict[UUID, str]:
    emails_by_user_id: dict[UUID, str] = {}
    local_result = await session.execute(
        select(local_credentials_table.c.user_id, local_credentials_table.c.login).where(
            local_credentials_table.c.user_id.in_(user_ids),
        ),
    )
    for row in local_result:
        emails_by_user_id[row.user_id] = row.login

    identity_result = await session.execute(
        select(identity_links_table.c.user_id, identity_links_table.c.email)
        .where(identity_links_table.c.user_id.in_(user_ids))
        .order_by(identity_links_table.c.created_at.asc()),
    )
    for row in identity_result:
        if row.email is not None and row.user_id not in emails_by_user_id:
            emails_by_user_id[row.user_id] = row.email

    return emails_by_user_id


async def _replace_local_role_assignments(
    session: AsyncSession,
    *,
    user_id: UUID,
    roles: tuple[Role, ...],
    timestamp: datetime,
) -> None:
    await session.execute(
        delete(role_assignments_table).where(
            role_assignments_table.c.user_id == user_id,
            role_assignments_table.c.source_provider == AuthProvider.LOCAL.value,
        ),
    )
    await _add_local_role_assignments(
        session,
        tuple(
            RoleAssignment(
                user_id=user_id,
                role=role,
                source_provider=AuthProvider.LOCAL,
                identity_link_id=None,
                created_at=timestamp,
                updated_at=timestamp,
            )
            for role in roles
        ),
    )


async def _add_local_role_assignments(
    session: AsyncSession,
    role_assignments: tuple[RoleAssignment, ...],
) -> None:
    if not role_assignments:
        return

    statement = postgresql_insert(role_assignments_table).values(
        [
            {
                "user_id": role_assignment.user_id,
                "role": role_assignment.role.value,
                "source_provider": role_assignment.source_provider.value,
                "identity_link_id": role_assignment.identity_link_id,
                "created_at": role_assignment.created_at,
                "updated_at": role_assignment.updated_at,
            }
            for role_assignment in role_assignments
        ],
    )
    await session.execute(
        statement.on_conflict_do_nothing(
            index_elements=[
                role_assignments_table.c.user_id,
                role_assignments_table.c.role,
                role_assignments_table.c.source_provider,
            ],
        ),
    )
