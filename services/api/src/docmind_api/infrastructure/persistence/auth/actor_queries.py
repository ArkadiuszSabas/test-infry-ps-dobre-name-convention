"""Read helpers for auth actor persistence projections."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.domain.auth.actors import AuthProvider
from docmind_api.infrastructure.persistence.auth.tables import (
    identity_links_table,
    local_credentials_table,
)


async def auth_providers_for_user(
    session: AsyncSession,
    user_id: UUID,
) -> frozenset[AuthProvider]:
    """Return all authentication providers currently available for one user."""

    providers_by_user_id = await auth_providers_for_users(session, (user_id,))
    return frozenset(providers_by_user_id[user_id])


async def auth_providers_for_users(
    session: AsyncSession,
    user_ids: tuple[UUID, ...],
) -> dict[UUID, tuple[AuthProvider, ...]]:
    """Return available authentication providers keyed by user id."""

    providers_by_user_id: dict[UUID, set[AuthProvider]] = {user_id: set() for user_id in user_ids}
    if not user_ids:
        return {}

    local_result = await session.execute(
        select(local_credentials_table.c.user_id).where(
            local_credentials_table.c.user_id.in_(user_ids),
        ),
    )
    for row in local_result:
        providers_by_user_id[row.user_id].add(AuthProvider.LOCAL)

    identity_result = await session.execute(
        select(identity_links_table.c.user_id, identity_links_table.c.provider).where(
            identity_links_table.c.user_id.in_(user_ids),
        ),
    )
    for row in identity_result:
        providers_by_user_id[row.user_id].add(AuthProvider(row.provider))

    return {
        user_id: tuple(sorted(providers, key=lambda provider: provider.value))
        for user_id, providers in providers_by_user_id.items()
    }
