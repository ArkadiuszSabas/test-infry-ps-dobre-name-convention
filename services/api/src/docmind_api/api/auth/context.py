"""Request-local auth context shared by API auth middleware and dependencies."""

from dataclasses import dataclass
from typing import cast

from fastapi import Request
from starlette.types import Scope

from docmind_api.domain.auth.actors import AuthenticatedActor

_AUTH_CONTEXT_STATE_KEY = "docmind_auth_context"


@dataclass(frozen=True, slots=True)
class AuthRequestContext:
    """Audit-safe authentication context for one HTTP request."""

    actor: AuthenticatedActor | None
    authorization_present: bool
    browser_session_present: bool

    @property
    def is_authenticated(self) -> bool:
        """Return whether the request resolved to a product actor."""

        return self.actor is not None


def set_auth_request_context(scope: Scope, context: AuthRequestContext) -> None:
    """Store auth context on ASGI request state."""

    state = scope.setdefault("state", {})
    if isinstance(state, dict):
        cast(dict[str, object], state)[_AUTH_CONTEXT_STATE_KEY] = context


def get_auth_request_context(request: Request) -> AuthRequestContext | None:
    """Return auth context previously attached to the FastAPI request."""

    state_object = request.scope.get("state")
    if not isinstance(state_object, dict):
        return None

    state = cast(dict[str, object], state_object)
    context = state.get(_AUTH_CONTEXT_STATE_KEY)
    if isinstance(context, AuthRequestContext):
        return context

    return None
