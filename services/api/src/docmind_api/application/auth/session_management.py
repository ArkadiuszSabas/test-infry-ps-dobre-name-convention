"""Self-service and admin browser session management use cases."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from docmind_api.application.auth.ports import (
    Clock,
    RefreshTokenFamilyRevoker,
    UserSessionRepository,
)
from docmind_api.application.auth.session_audit import (
    log_refresh_credentials_revoked,
    log_session_revoked,
)
from docmind_api.domain.auth.actors import AuthenticatedActor
from docmind_api.domain.auth.sessions import SessionRevocationReason, UserSession
from docmind_backend_runtime.errors import NotFoundError


@dataclass(frozen=True, slots=True)
class ListUserSessionsCommand:
    """Input for listing sessions for a concrete user."""

    user_id: UUID


@dataclass(frozen=True, slots=True)
class ListOwnUserSessionsCommand:
    """Input for listing sessions owned by the current actor."""

    actor: AuthenticatedActor


@dataclass(frozen=True, slots=True)
class RevokeOwnUserSessionCommand:
    """Input for revoking a current actor's selected session."""

    actor: AuthenticatedActor
    session_id: UUID


@dataclass(frozen=True, slots=True)
class RevokeUserSessionForUserCommand:
    """Input for revoking a selected session owned by a concrete user."""

    user_id: UUID
    session_id: UUID


@dataclass(frozen=True, slots=True)
class UserSessionListResult:
    """Result of listing browser sessions."""

    sessions: tuple[UserSession, ...]
    evaluated_at: datetime


@dataclass(frozen=True, slots=True)
class ManagedUserSessionRevocationResult:
    """Result of revoking a session by id."""

    session: UserSession
    revoked: bool
    evaluated_at: datetime


class UserSessionNotFoundError(NotFoundError):
    """Raised when a requested user session is not visible to the actor."""

    def __init__(self) -> None:
        super().__init__(
            code="USER_SESSION_NOT_FOUND",
            message="User session not found.",
        )


class UserSessionManagementService:
    """Application service for self-service and admin session management."""

    def __init__(
        self,
        *,
        repository: UserSessionRepository,
        refresh_family_revoker: RefreshTokenFamilyRevoker,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._refresh_family_revoker = refresh_family_revoker
        self._clock = clock

    async def list_own_sessions(
        self,
        command: ListOwnUserSessionsCommand,
    ) -> UserSessionListResult:
        """Return sessions visible to the current actor."""

        return await self.list_user_sessions(
            ListUserSessionsCommand(user_id=_actor_user_id(command.actor)),
        )

    async def list_user_sessions(
        self,
        command: ListUserSessionsCommand,
    ) -> UserSessionListResult:
        """Return sessions for a concrete user."""

        sessions = await self._repository.list_for_user(command.user_id)
        return UserSessionListResult(sessions=sessions, evaluated_at=self._clock.now())

    async def revoke_own_session(
        self,
        command: RevokeOwnUserSessionCommand,
    ) -> ManagedUserSessionRevocationResult:
        """Revoke a current actor's selected browser session."""

        return await self._revoke_user_session(
            user_id=_actor_user_id(command.actor),
            session_id=command.session_id,
            actor_id=command.actor.actor_id,
            reason=SessionRevocationReason.USER_REVOKED,
        )

    async def revoke_user_session(
        self,
        command: RevokeUserSessionForUserCommand,
        *,
        actor: AuthenticatedActor,
    ) -> ManagedUserSessionRevocationResult:
        """Revoke a selected browser session for an administratively managed user."""

        return await self._revoke_user_session(
            user_id=command.user_id,
            session_id=command.session_id,
            actor_id=actor.actor_id,
            reason=SessionRevocationReason.ADMIN_REVOKED,
        )

    async def _revoke_user_session(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        actor_id: str,
        reason: SessionRevocationReason,
    ) -> ManagedUserSessionRevocationResult:
        timestamp = self._clock.now()
        session = await self._repository.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise UserSessionNotFoundError()

        if not session.is_active_at(timestamp):
            return ManagedUserSessionRevocationResult(
                session=session,
                revoked=False,
                evaluated_at=timestamp,
            )

        revoked = await self._refresh_family_revoker.revoke_session_family(
            session.id,
            timestamp,
            reason,
        )
        if revoked:
            log_refresh_credentials_revoked(
                actor_id=actor_id,
                target_user_id=str(user_id),
                session_id=str(session.id),
                refresh_token_family_id=None,
                reason=reason,
            )
        else:
            revoked = await self._repository.revoke(session.id, timestamp, reason)
        revoked_session = session.revoke(revoked_at=timestamp, reason=reason)
        if revoked:
            log_session_revoked(
                actor_id=actor_id,
                target_user_id=str(user_id),
                session_id=str(session.id),
                reason=reason,
            )
        return ManagedUserSessionRevocationResult(
            session=revoked_session,
            revoked=revoked,
            evaluated_at=timestamp,
        )


def _actor_user_id(actor: AuthenticatedActor) -> UUID:
    return UUID(actor.actor_id)
