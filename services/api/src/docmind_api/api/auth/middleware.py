"""Auth context middleware for the API service."""

import logging
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from http.cookies import CookieError, SimpleCookie

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from docmind_api.api.auth.context import AuthRequestContext, set_auth_request_context
from docmind_api.api.auth.dependencies import DOCMIND_SESSION_COOKIE
from docmind_api.application.auth.ports import ActorCredentials
from docmind_api.domain.auth.actors import AuthenticatedActor
from docmind_backend_runtime.context import get_correlation_id

ResolveAuthContextActor = Callable[
    [Scope, ActorCredentials],
    Awaitable[AuthenticatedActor | None],
]

_PUBLIC_AUTH_CONTEXT_PATHS = frozenset(
    {
        "/",
        "/docs",
        "/docs/oauth2-redirect",
        "/health/live",
        "/health/ready",
        "/openapi.json",
        "/redoc",
        "/auth/csrf",
        "/auth/entra/callback",
        "/auth/entra/start",
        "/auth/local/login",
        "/auth/logout",
        "/auth/refresh",
    }
)
_SAFE_AUTH_CONTEXT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_AUTH_CONTEXT_LOGGER = logging.getLogger("docmind_api.auth.context")


class AuthContextMiddleware:
    """Resolve API-owned browser session context once per request."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        resolve_actor: ResolveAuthContextActor,
        correlation_header_name: str = "X-Correlation-Id",
    ) -> None:
        self._app = app
        self._resolve_actor = resolve_actor
        self._correlation_header_name = correlation_header_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        credentials = _credentials_from_scope(scope)
        if _should_skip_auth_context(scope, credentials):
            await self._app(scope, receive, send)
            return

        actor: AuthenticatedActor | None = None
        if _should_resolve_actor(scope, credentials):
            try:
                actor = await self._resolve_actor(scope, credentials)
            except Exception as exc:
                _log_auth_context_resolution_failed(exc)
                await _send_internal_error_response(
                    scope=scope,
                    receive=receive,
                    send=send,
                    correlation_header_name=self._correlation_header_name,
                )
                return

        set_auth_request_context(
            scope,
            AuthRequestContext(
                actor=actor,
                authorization_present=_has_value(credentials.authorization),
                browser_session_present=_has_value(credentials.session_id),
            ),
        )
        await self._app(scope, receive, send)


def _credentials_from_scope(scope: Scope) -> ActorCredentials:
    headers = Headers(scope=scope)
    return ActorCredentials(
        authorization=headers.get("authorization"),
        session_id=_session_cookie_from_headers(headers),
    )


def _session_cookie_from_headers(headers: Headers) -> str | None:
    cookie_header = headers.get("cookie")
    if cookie_header is None or not cookie_header.strip():
        return None

    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except CookieError:
        return None

    morsel = cookie.get(DOCMIND_SESSION_COOKIE)
    if morsel is None:
        return None

    return morsel.value


def _should_skip_auth_context(scope: Scope, credentials: ActorCredentials) -> bool:
    method = scope.get("method")
    if not isinstance(method, str) or method.upper() in _SAFE_AUTH_CONTEXT_METHODS:
        return False

    return _has_value(credentials.session_id)


def _should_resolve_actor(scope: Scope, credentials: ActorCredentials) -> bool:
    if not _has_value(credentials.session_id):
        return False

    path = scope.get("path")
    normalized_path = path.rstrip("/") if isinstance(path, str) else ""
    if (normalized_path or "/") in _PUBLIC_AUTH_CONTEXT_PATHS:
        return False

    return True


def _has_value(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _log_auth_context_resolution_failed(exc: Exception) -> None:
    _AUTH_CONTEXT_LOGGER.error(
        "Auth context resolution failed.",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={
            "correlation_id": get_correlation_id(),
            "exception_type": type(exc).__name__,
        },
    )


async def _send_internal_error_response(
    *,
    scope: Scope,
    receive: Receive,
    send: Send,
    correlation_header_name: str,
) -> None:
    response = JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error.",
                "details": {},
            },
        },
    )
    correlation_id = get_correlation_id()
    if correlation_id is not None:
        response.headers[correlation_header_name] = correlation_id

    await response(scope, receive, send)
