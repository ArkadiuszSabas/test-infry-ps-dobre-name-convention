"""Provider-neutral actor resolver adapters."""

from typing import Protocol

from docmind_api.application.auth.ports import ActorCredentials, OpaqueSessionToken
from docmind_api.application.auth.sessions import ResolveUserSessionCommand
from docmind_api.domain.auth.actors import AuthenticatedActor


class _SessionActorService(Protocol):
    async def resolve_actor(
        self,
        command: ResolveUserSessionCommand,
    ) -> AuthenticatedActor | None: ...


class RejectingActorResolver:
    """Resolver that rejects every request until auth providers are wired."""

    async def resolve_actor(
        self,
        credentials: ActorCredentials,
    ) -> AuthenticatedActor | None:
        """Return no actor because no auth provider is configured yet."""

        return None


class SessionActorResolver:
    """Resolve actors from DocMind browser session credentials."""

    def __init__(
        self,
        session_service: _SessionActorService,
        *,
        touch_last_seen: bool = True,
    ) -> None:
        self._session_service = session_service
        self._touch_last_seen = touch_last_seen

    async def resolve_actor(
        self,
        credentials: ActorCredentials,
    ) -> AuthenticatedActor | None:
        """Return an actor when the DocMind session cookie is valid."""

        if credentials.session_id is None or not credentials.session_id.strip():
            return None

        return await self._session_service.resolve_actor(
            ResolveUserSessionCommand(
                token=OpaqueSessionToken(credentials.session_id),
                touch_last_seen=self._touch_last_seen,
            ),
        )
