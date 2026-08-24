"""Session refresh token persistence adapters."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docmind_api.application.auth.ports import (
    RefreshTokenFamilyRevoker,
    RefreshTokenRepository,
    UserSessionBulkRevoker,
)
from docmind_api.domain.auth.sessions import (
    RefreshTokenHash,
    SessionRefreshToken,
    SessionRevocationReason,
)
from docmind_api.infrastructure.persistence.auth.tables import (
    session_refresh_tokens_table,
    user_sessions_table,
)
from docmind_api.infrastructure.persistence.sql import database_session_scope


class SqlAlchemySessionRefreshTokenRepository(RefreshTokenRepository):
    """PostgreSQL-backed browser refresh token repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_token_hash(
        self,
        token_hash: RefreshTokenHash,
    ) -> SessionRefreshToken | None:
        """Return a refresh token by persisted token hash."""

        statement = select(session_refresh_tokens_table).where(
            session_refresh_tokens_table.c.token_hash == token_hash.value,
        )
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return _session_refresh_token_from_row(row)

    async def add(self, refresh_token: SessionRefreshToken) -> None:
        """Store a browser refresh token in PostgreSQL."""

        await self._session.execute(
            insert(session_refresh_tokens_table).values(
                id=refresh_token.id,
                family_id=refresh_token.family_id,
                session_id=refresh_token.session_id,
                token_hash=refresh_token.token_hash.value,
                created_at=refresh_token.created_at,
                expires_at=refresh_token.expires_at,
                rotated_at=refresh_token.rotated_at,
                revoked_at=refresh_token.revoked_at,
                reused_at=refresh_token.reused_at,
            ),
        )

    async def mark_rotated(self, refresh_token_id: UUID, rotated_at: datetime) -> bool:
        """Mark a refresh token as rotated after a successful use."""

        statement = (
            update(session_refresh_tokens_table)
            .where(
                session_refresh_tokens_table.c.id == refresh_token_id,
                session_refresh_tokens_table.c.rotated_at.is_(None),
                session_refresh_tokens_table.c.revoked_at.is_(None),
                session_refresh_tokens_table.c.reused_at.is_(None),
            )
            .values(rotated_at=rotated_at)
            .returning(session_refresh_tokens_table.c.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def mark_reused(self, refresh_token_id: UUID, reused_at: datetime) -> None:
        """Mark a rotated refresh token as reused."""

        await _mark_reused(self._session, refresh_token_id, reused_at)

    async def revoke_family(self, family_id: UUID, revoked_at: datetime) -> None:
        """Mark all tokens in a refresh token family as revoked."""

        await _revoke_refresh_family(self._session, family_id, revoked_at)


class SqlAlchemyRefreshTokenFamilyRevoker(RefreshTokenFamilyRevoker):
    """Durably revoke refresh token families and their issued browser sessions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def revoke_family(
        self,
        family_id: UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> bool:
        """Revoke refresh tokens and browser sessions issued from a family."""

        async with database_session_scope(self._session_factory) as session:
            refresh_rows, session_rows = await _revoke_refresh_families_and_sessions(
                session,
                (family_id,),
                revoked_at,
                reason,
            )
            return refresh_rows > 0 or session_rows > 0

    async def record_reuse_and_revoke_family(
        self,
        *,
        refresh_token_id: UUID,
        family_id: UUID,
        reused_at: datetime,
    ) -> None:
        """Record refresh-token reuse and revoke the whole family durably."""

        async with database_session_scope(self._session_factory) as session:
            await _mark_reused(session, refresh_token_id, reused_at)
            await _revoke_refresh_families_and_sessions(
                session,
                (family_id,),
                reused_at,
                SessionRevocationReason.UNKNOWN,
            )

    async def revoke_session_family(
        self,
        session_id: UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> bool:
        """Revoke refresh families associated with one browser session."""

        async with database_session_scope(self._session_factory) as session:
            family_ids = await _family_ids_for_session(session, session_id)
            if not family_ids:
                return False

            refresh_rows, session_rows = await _revoke_refresh_families_and_sessions(
                session,
                family_ids,
                revoked_at,
                reason,
            )
            return refresh_rows > 0 or session_rows > 0


class SqlAlchemySessionBoundRefreshTokenFamilyRevoker(RefreshTokenFamilyRevoker):
    """Revoke refresh token families inside an existing request unit of work."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def revoke_family(
        self,
        family_id: UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> bool:
        """Revoke refresh tokens and browser sessions issued from a family."""

        refresh_rows, session_rows = await _revoke_refresh_families_and_sessions(
            self._session,
            (family_id,),
            revoked_at,
            reason,
        )
        return refresh_rows > 0 or session_rows > 0

    async def record_reuse_and_revoke_family(
        self,
        *,
        refresh_token_id: UUID,
        family_id: UUID,
        reused_at: datetime,
    ) -> None:
        """Record refresh-token reuse and revoke the whole family."""

        await _mark_reused(self._session, refresh_token_id, reused_at)
        await _revoke_refresh_families_and_sessions(
            self._session,
            (family_id,),
            reused_at,
            SessionRevocationReason.UNKNOWN,
        )

    async def revoke_session_family(
        self,
        session_id: UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> bool:
        """Revoke refresh families associated with one browser session."""

        family_ids = await _family_ids_for_session(self._session, session_id)
        if not family_ids:
            return False

        refresh_rows, session_rows = await _revoke_refresh_families_and_sessions(
            self._session,
            family_ids,
            revoked_at,
            reason,
        )
        return refresh_rows > 0 or session_rows > 0


class SqlAlchemyUserSessionBulkRevoker(UserSessionBulkRevoker):
    """Revoke all refresh credentials and browser sessions for a user."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def revoke_all_for_user(
        self,
        user_id: UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> int:
        """Mark all unrevoked sessions and refresh tokens for a user as revoked."""

        family_ids = await _family_ids_for_user(self._session, user_id)
        if family_ids:
            await _revoke_refresh_families(self._session, family_ids, revoked_at)

        return await _revoke_sessions_for_user(
            self._session,
            user_id,
            revoked_at,
            reason,
        )


async def _mark_reused(
    session: AsyncSession,
    refresh_token_id: UUID,
    reused_at: datetime,
) -> int:
    statement = (
        update(session_refresh_tokens_table)
        .where(
            session_refresh_tokens_table.c.id == refresh_token_id,
            session_refresh_tokens_table.c.reused_at.is_(None),
        )
        .values(reused_at=reused_at)
        .returning(session_refresh_tokens_table.c.id)
    )
    result = await session.execute(statement)
    return len(result.scalars().all())


async def _revoke_refresh_family(
    session: AsyncSession,
    family_id: UUID,
    revoked_at: datetime,
) -> int:
    return await _revoke_refresh_families(session, (family_id,), revoked_at)


async def _revoke_refresh_families_and_sessions(
    session: AsyncSession,
    family_ids: tuple[UUID, ...],
    revoked_at: datetime,
    reason: SessionRevocationReason,
) -> tuple[int, int]:
    refresh_rows = await _revoke_refresh_families(session, family_ids, revoked_at)
    session_rows = await _revoke_sessions_for_families(
        session,
        family_ids,
        revoked_at,
        reason,
    )
    refresh_rows += await _revoke_refresh_families(session, family_ids, revoked_at)
    return refresh_rows, session_rows


async def _revoke_refresh_families(
    session: AsyncSession,
    family_ids: tuple[UUID, ...],
    revoked_at: datetime,
) -> int:
    statement = (
        update(session_refresh_tokens_table)
        .where(
            session_refresh_tokens_table.c.family_id.in_(family_ids),
            session_refresh_tokens_table.c.revoked_at.is_(None),
        )
        .values(revoked_at=revoked_at)
        .returning(session_refresh_tokens_table.c.id)
    )
    result = await session.execute(statement)
    return len(result.scalars().all())


async def _revoke_sessions_for_families(
    session: AsyncSession,
    family_ids: tuple[UUID, ...],
    revoked_at: datetime,
    reason: SessionRevocationReason,
) -> int:
    family_session_ids = select(session_refresh_tokens_table.c.session_id).where(
        session_refresh_tokens_table.c.family_id.in_(family_ids),
    )
    statement = (
        update(user_sessions_table)
        .where(
            user_sessions_table.c.id.in_(family_session_ids),
            user_sessions_table.c.revoked_at.is_(None),
        )
        .values(revoked_at=revoked_at, revoked_reason=reason.value)
        .returning(user_sessions_table.c.id)
    )
    result = await session.execute(statement)
    return len(result.scalars().all())


async def _family_ids_for_session(
    session: AsyncSession,
    session_id: UUID,
) -> tuple[UUID, ...]:
    statement = (
        select(session_refresh_tokens_table.c.family_id)
        .where(session_refresh_tokens_table.c.session_id == session_id)
        .distinct()
    )
    result = await session.execute(statement)
    return tuple(result.scalars().all())


async def _family_ids_for_user(
    session: AsyncSession,
    user_id: UUID,
) -> tuple[UUID, ...]:
    statement = (
        select(session_refresh_tokens_table.c.family_id)
        .select_from(session_refresh_tokens_table)
        .join(
            user_sessions_table,
            user_sessions_table.c.id == session_refresh_tokens_table.c.session_id,
        )
        .where(user_sessions_table.c.user_id == user_id)
        .distinct()
    )
    result = await session.execute(statement)
    return tuple(result.scalars().all())


async def _revoke_sessions_for_user(
    session: AsyncSession,
    user_id: UUID,
    revoked_at: datetime,
    reason: SessionRevocationReason,
) -> int:
    statement = (
        update(user_sessions_table)
        .where(
            user_sessions_table.c.user_id == user_id,
            user_sessions_table.c.revoked_at.is_(None),
        )
        .values(revoked_at=revoked_at, revoked_reason=reason.value)
        .returning(user_sessions_table.c.id)
    )
    result = await session.execute(statement)
    return len(result.scalars().all())


def _session_refresh_token_from_row(row: Any) -> SessionRefreshToken:
    return SessionRefreshToken(
        id=row["id"],
        family_id=row["family_id"],
        session_id=row["session_id"],
        token_hash=RefreshTokenHash(row["token_hash"]),
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        rotated_at=row["rotated_at"],
        revoked_at=row["revoked_at"],
        reused_at=row["reused_at"],
    )
