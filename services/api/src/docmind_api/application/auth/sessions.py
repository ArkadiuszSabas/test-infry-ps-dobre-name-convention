"""Browser session issuance and token-backed resolution use cases."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Protocol
from uuid import UUID

from docmind_api.application.auth.ports import (
    Clock,
    CsrfTokenCodec,
    OpaqueCsrfToken,
    OpaqueRefreshToken,
    OpaqueSessionToken,
    RefreshTokenFamilyIdGenerator,
    RefreshTokenFamilyRevoker,
    RefreshTokenGenerator,
    RefreshTokenHasher,
    RefreshTokenIdGenerator,
    RefreshTokenRepository,
    SessionActorContext,
    SessionActorRepository,
    SessionTokenGenerator,
    SessionTokenHasher,
    UserSessionIdGenerator,
    UserSessionRepository,
)
from docmind_api.application.auth.session_audit import (
    log_refresh_credentials_revoked,
    log_refresh_token_reuse_detected,
    log_session_revoked,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, AuthProvider
from docmind_api.domain.auth.sessions import (
    SessionClientMetadata,
    SessionRefreshToken,
    SessionRevocationReason,
    UserSession,
)
from docmind_backend_runtime.errors import ApplicationError


@dataclass(frozen=True, slots=True)
class IssueBrowserSessionCommand:
    """Input for creating an API-owned browser session."""

    user_id: UUID
    auth_provider: AuthProvider
    identity_link_id: UUID | None = None
    refresh_token_family_id: UUID | None = None
    resolved_actor: AuthenticatedActor | None = None
    client_metadata: SessionClientMetadata = field(default_factory=SessionClientMetadata)


@dataclass(frozen=True, slots=True)
class ResolveUserSessionCommand:
    """Input for resolving a browser session token."""

    token: OpaqueSessionToken = field(repr=False)
    touch_last_seen: bool = True


@dataclass(frozen=True, slots=True)
class RevokeUserSessionCommand:
    """Input for revoking a browser session token."""

    token: OpaqueSessionToken = field(repr=False)
    reason: SessionRevocationReason = SessionRevocationReason.USER_LOGOUT


@dataclass(frozen=True, slots=True)
class RefreshBrowserSessionCommand:
    """Input for rotating a browser session using a refresh token."""

    token: OpaqueRefreshToken = field(repr=False)


@dataclass(frozen=True, slots=True)
class RevokeRefreshTokenFamilyCommand:
    """Input for revoking the refresh token family behind a raw token."""

    token: OpaqueRefreshToken = field(repr=False)
    reason: SessionRevocationReason = SessionRevocationReason.USER_LOGOUT


@dataclass(frozen=True, slots=True)
class IssueCsrfTokenCommand:
    """Input for issuing a session-bound CSRF token."""

    token: OpaqueSessionToken = field(repr=False)


@dataclass(frozen=True, slots=True)
class ValidateCsrfTokenCommand:
    """Input for validating a CSRF token against a browser session."""

    session_token: OpaqueSessionToken = field(repr=False)
    csrf_token: OpaqueCsrfToken = field(repr=False)


@dataclass(frozen=True, slots=True)
class IssuedBrowserSession:
    """Issued browser session, actor, and raw tokens for response cookies."""

    actor: AuthenticatedActor
    session: UserSession
    refresh_token_record: SessionRefreshToken
    token: OpaqueSessionToken = field(repr=False)
    refresh_token: OpaqueRefreshToken = field(repr=False)
    csrf_token: OpaqueCsrfToken = field(repr=False)


@dataclass(frozen=True, slots=True)
class RevokeUserSessionResult:
    """Result of attempting to revoke a browser session."""

    revoked: bool


@dataclass(frozen=True, slots=True)
class RevokeRefreshTokenFamilyResult:
    """Result of attempting to revoke a refresh token family."""

    revoked: bool


@dataclass(frozen=True, slots=True)
class IssuedCsrfToken:
    """Issued session-bound CSRF token."""

    token: OpaqueCsrfToken = field(repr=False)


class InvalidRefreshTokenError(ApplicationError):
    """Raised when a refresh token cannot issue a new browser session."""

    def __init__(self) -> None:
        super().__init__(
            code="INVALID_REFRESH_TOKEN",
            message="Refresh token is invalid.",
            status_code=HTTPStatus.UNAUTHORIZED,
        )


class BrowserSessionIssuer(Protocol):
    """Application boundary for use cases that issue DocMind browser sessions."""

    async def execute(
        self,
        command: IssueBrowserSessionCommand,
    ) -> IssuedBrowserSession | None: ...


class CsrfTokenValidator(Protocol):
    """Application boundary used by HTTP dependencies to validate CSRF tokens."""

    async def resolve_session(
        self,
        command: ResolveUserSessionCommand,
    ) -> UserSession | None:
        """Return an active session when the cookie token is valid."""
        ...

    async def validate_csrf_token(self, command: ValidateCsrfTokenCommand) -> bool:
        """Return whether a CSRF token belongs to an active browser session."""
        ...


class IssueBrowserSessionUseCase:
    """Application use case for issuing DocMind browser sessions."""

    def __init__(
        self,
        *,
        repository: UserSessionRepository,
        actor_repository: SessionActorRepository,
        token_generator: SessionTokenGenerator,
        token_hasher: SessionTokenHasher,
        refresh_repository: RefreshTokenRepository,
        refresh_token_generator: RefreshTokenGenerator,
        refresh_token_hasher: RefreshTokenHasher,
        csrf_token_codec: CsrfTokenCodec,
        clock: Clock,
        id_generator: UserSessionIdGenerator,
        refresh_token_id_generator: RefreshTokenIdGenerator,
        refresh_token_family_id_generator: RefreshTokenFamilyIdGenerator,
        session_lifetime: timedelta,
        refresh_token_lifetime: timedelta,
    ) -> None:
        if session_lifetime <= timedelta(0):
            raise ValueError("User session lifetime must be positive.")
        if refresh_token_lifetime <= timedelta(0):
            raise ValueError("Refresh token lifetime must be positive.")

        self._repository = repository
        self._actor_repository = actor_repository
        self._token_generator = token_generator
        self._token_hasher = token_hasher
        self._refresh_repository = refresh_repository
        self._refresh_token_generator = refresh_token_generator
        self._refresh_token_hasher = refresh_token_hasher
        self._csrf_token_codec = csrf_token_codec
        self._clock = clock
        self._id_generator = id_generator
        self._refresh_token_id_generator = refresh_token_id_generator
        self._refresh_token_family_id_generator = refresh_token_family_id_generator
        self._session_lifetime = session_lifetime
        self._refresh_token_lifetime = refresh_token_lifetime

    async def execute(
        self,
        command: IssueBrowserSessionCommand,
    ) -> IssuedBrowserSession | None:
        """Create and persist a browser session for a session-resolvable user."""

        actor = command.resolved_actor
        if actor is not None:
            if actor.actor_id != str(command.user_id) or actor.provider != command.auth_provider:
                return None
        else:
            actor = await self._actor_repository.get_actor_for_session(
                SessionActorContext(
                    user_id=command.user_id,
                    auth_provider=command.auth_provider,
                    identity_link_id=command.identity_link_id,
                )
            )
            if actor is None:
                return None

        timestamp = self._clock.now()
        token = self._token_generator.new_token()
        session = UserSession(
            id=self._id_generator.new_id(),
            user_id=command.user_id,
            token_hash=self._token_hasher.hash_token(token),
            created_at=timestamp,
            last_seen_at=timestamp,
            expires_at=timestamp + self._session_lifetime,
            auth_provider=command.auth_provider,
            identity_link_id=command.identity_link_id,
            client_label=command.client_metadata.client_label,
            client_fingerprint=command.client_metadata.client_fingerprint,
        )

        await self._repository.add(session)
        refresh_token = self._refresh_token_generator.new_token()
        refresh_token_record = SessionRefreshToken(
            id=self._refresh_token_id_generator.new_id(),
            family_id=command.refresh_token_family_id
            or self._refresh_token_family_id_generator.new_id(),
            session_id=session.id,
            token_hash=self._refresh_token_hasher.hash_token(refresh_token),
            created_at=timestamp,
            expires_at=timestamp + self._refresh_token_lifetime,
        )
        await self._refresh_repository.add(refresh_token_record)

        return IssuedBrowserSession(
            actor=actor,
            session=session,
            token=token,
            refresh_token=refresh_token,
            refresh_token_record=refresh_token_record,
            csrf_token=self._csrf_token_codec.issue_token(
                session_token_hash=session.token_hash,
            ),
        )


class UserSessionService:
    """Application service for resolving and revoking DocMind browser sessions."""

    def __init__(
        self,
        *,
        repository: UserSessionRepository,
        actor_repository: SessionActorRepository,
        token_hasher: SessionTokenHasher,
        refresh_repository: RefreshTokenRepository,
        refresh_family_revoker: RefreshTokenFamilyRevoker,
        refresh_token_hasher: RefreshTokenHasher,
        session_issuer: BrowserSessionIssuer,
        csrf_token_codec: CsrfTokenCodec,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._actor_repository = actor_repository
        self._token_hasher = token_hasher
        self._refresh_repository = refresh_repository
        self._refresh_family_revoker = refresh_family_revoker
        self._refresh_token_hasher = refresh_token_hasher
        self._session_issuer = session_issuer
        self._csrf_token_codec = csrf_token_codec
        self._clock = clock

    async def resolve_session(
        self,
        command: ResolveUserSessionCommand,
    ) -> UserSession | None:
        """Resolve an active browser session from a raw session token."""

        timestamp = self._clock.now()
        session = await self._repository.get_by_token_hash(
            self._token_hasher.hash_token(command.token),
        )
        if session is None:
            return None

        if not session.is_active_at(timestamp):
            return None

        if not command.touch_last_seen:
            return session

        await self._repository.touch(session.id, timestamp)
        return session.mark_seen(last_seen_at=timestamp)

    async def resolve_actor(
        self,
        command: ResolveUserSessionCommand,
    ) -> AuthenticatedActor | None:
        """Resolve a provider-neutral actor from an active browser session."""

        session = await self.resolve_session(command)
        if session is None:
            return None

        return await self._actor_repository.get_actor_for_session(
            SessionActorContext(
                user_id=session.user_id,
                auth_provider=session.auth_provider,
                identity_link_id=session.identity_link_id,
            )
        )

    async def revoke_session(
        self,
        command: RevokeUserSessionCommand,
    ) -> RevokeUserSessionResult:
        """Revoke an active browser session from a raw session token."""

        timestamp = self._clock.now()
        session = await self._repository.get_by_token_hash(
            self._token_hasher.hash_token(command.token),
        )
        if session is None:
            return RevokeUserSessionResult(revoked=False)

        if not session.is_active_at(timestamp):
            return RevokeUserSessionResult(revoked=False)

        revoked = await self._refresh_family_revoker.revoke_session_family(
            session.id,
            timestamp,
            command.reason,
        )
        if revoked:
            log_refresh_credentials_revoked(
                actor_id=str(session.user_id),
                target_user_id=str(session.user_id),
                session_id=str(session.id),
                refresh_token_family_id=None,
                reason=command.reason,
            )
        else:
            revoked = await self._repository.revoke(session.id, timestamp, command.reason)
        if revoked:
            log_session_revoked(
                actor_id=str(session.user_id),
                target_user_id=str(session.user_id),
                session_id=str(session.id),
                reason=command.reason,
            )
        return RevokeUserSessionResult(revoked=revoked)

    async def refresh_session(
        self,
        command: RefreshBrowserSessionCommand,
    ) -> IssuedBrowserSession:
        """Rotate a refresh token and issue a new DocMind browser session."""

        timestamp = self._clock.now()
        refresh_token = await self._refresh_repository.get_by_token_hash(
            self._refresh_token_hasher.hash_token(command.token),
        )
        if refresh_token is None:
            raise InvalidRefreshTokenError()

        if not refresh_token.is_active_at(timestamp):
            await self._record_refresh_reuse_if_needed(
                refresh_token=refresh_token,
                timestamp=timestamp,
            )
            raise InvalidRefreshTokenError()

        session = await self._repository.get_by_id(refresh_token.session_id)
        if session is None or session.is_revoked:
            family_revoked = await self._refresh_family_revoker.revoke_family(
                refresh_token.family_id,
                timestamp,
                SessionRevocationReason.UNKNOWN,
            )
            if family_revoked:
                log_refresh_credentials_revoked(
                    actor_id=None,
                    target_user_id=str(session.user_id) if session is not None else None,
                    session_id=str(refresh_token.session_id),
                    refresh_token_family_id=str(refresh_token.family_id),
                    reason=SessionRevocationReason.UNKNOWN,
                )
            raise InvalidRefreshTokenError()

        actor = await self._actor_repository.get_actor_for_session(
            SessionActorContext(
                user_id=session.user_id,
                auth_provider=session.auth_provider,
                identity_link_id=session.identity_link_id,
            )
        )
        if actor is None:
            family_revoked = await self._refresh_family_revoker.revoke_family(
                family_id=refresh_token.family_id,
                revoked_at=timestamp,
                reason=SessionRevocationReason.UNKNOWN,
            )
            if family_revoked:
                log_refresh_credentials_revoked(
                    actor_id=None,
                    target_user_id=str(session.user_id),
                    session_id=str(session.id),
                    refresh_token_family_id=str(refresh_token.family_id),
                    reason=SessionRevocationReason.UNKNOWN,
                )
            raise InvalidRefreshTokenError()

        token_rotated = await self._refresh_repository.mark_rotated(
            refresh_token.id,
            timestamp,
        )
        if not token_rotated:
            await self._refresh_family_revoker.record_reuse_and_revoke_family(
                refresh_token_id=refresh_token.id,
                family_id=refresh_token.family_id,
                reused_at=timestamp,
            )
            log_refresh_token_reuse_detected(
                target_user_id=str(session.user_id),
                session_id=str(session.id),
                refresh_token_id=str(refresh_token.id),
                refresh_token_family_id=str(refresh_token.family_id),
            )
            raise InvalidRefreshTokenError()

        issued_session = await self._session_issuer.execute(
            IssueBrowserSessionCommand(
                user_id=session.user_id,
                auth_provider=session.auth_provider,
                identity_link_id=session.identity_link_id,
                refresh_token_family_id=refresh_token.family_id,
                resolved_actor=actor,
                client_metadata=SessionClientMetadata(
                    client_label=session.client_label,
                    client_fingerprint=session.client_fingerprint,
                ),
            )
        )
        if issued_session is None:
            raise RuntimeError("Refresh session issuer failed after eligibility check.")

        return issued_session

    async def revoke_refresh_token_family(
        self,
        command: RevokeRefreshTokenFamilyCommand,
    ) -> RevokeRefreshTokenFamilyResult:
        """Revoke the refresh token family represented by a raw refresh token."""

        timestamp = self._clock.now()
        refresh_token = await self._refresh_repository.get_by_token_hash(
            self._refresh_token_hasher.hash_token(command.token),
        )
        if refresh_token is None:
            return RevokeRefreshTokenFamilyResult(revoked=False)

        session = await self._repository.get_by_id(refresh_token.session_id)
        revoked = await self._refresh_family_revoker.revoke_family(
            refresh_token.family_id,
            timestamp,
            command.reason,
        )
        if revoked:
            log_refresh_credentials_revoked(
                actor_id=str(session.user_id) if session is not None else None,
                target_user_id=str(session.user_id) if session is not None else None,
                session_id=str(session.id)
                if session is not None
                else str(refresh_token.session_id),
                refresh_token_family_id=str(refresh_token.family_id),
                reason=command.reason,
            )
        return RevokeRefreshTokenFamilyResult(revoked=revoked)

    async def issue_csrf_token(
        self,
        command: IssueCsrfTokenCommand,
    ) -> IssuedCsrfToken | None:
        """Issue a CSRF token for an active browser session."""

        session = await self.resolve_session(
            ResolveUserSessionCommand(token=command.token),
        )
        if session is None:
            return None

        return IssuedCsrfToken(
            token=self._csrf_token_codec.issue_token(
                session_token_hash=session.token_hash,
            ),
        )

    async def validate_csrf_token(
        self,
        command: ValidateCsrfTokenCommand,
    ) -> bool:
        """Return whether a CSRF token is valid for an active browser session."""

        session = await self.resolve_session(
            ResolveUserSessionCommand(
                token=command.session_token,
                touch_last_seen=False,
            ),
        )
        if session is None:
            return False

        return self._csrf_token_codec.verify_token(
            token=command.csrf_token,
            session_token_hash=session.token_hash,
        )

    async def _record_refresh_reuse_if_needed(
        self,
        *,
        refresh_token: SessionRefreshToken,
        timestamp: datetime,
    ) -> None:
        if not refresh_token.is_rotated:
            return

        await self._refresh_family_revoker.record_reuse_and_revoke_family(
            refresh_token_id=refresh_token.id,
            family_id=refresh_token.family_id,
            reused_at=timestamp,
        )
        session = await self._repository.get_by_id(refresh_token.session_id)
        log_refresh_token_reuse_detected(
            target_user_id=str(session.user_id) if session is not None else None,
            session_id=str(session.id) if session is not None else str(refresh_token.session_id),
            refresh_token_id=str(refresh_token.id),
            refresh_token_family_id=str(refresh_token.family_id),
        )
