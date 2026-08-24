"""FastAPI authorization dependencies for protected API endpoints."""

import logging
from collections.abc import Awaitable, Callable
from typing import Annotated
from urllib.parse import urlsplit, urlunsplit

from fastapi import Cookie, Depends, Header, Request

from docmind_api.api.auth.context import get_auth_request_context
from docmind_api.application.auth.ports import (
    ActorCredentials,
    ActorResolver,
    OpaqueCsrfToken,
    OpaqueSessionToken,
)
from docmind_api.application.auth.sessions import (
    CsrfTokenValidator,
    ResolveUserSessionCommand,
    ValidateCsrfTokenCommand,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission
from docmind_backend_runtime.context import get_correlation_id
from docmind_backend_runtime.errors import ApplicationError

DOCMIND_SESSION_COOKIE = "__Host-docmind_session"
DOCMIND_REFRESH_COOKIE = "__Host-docmind_refresh"
CSRF_HEADER = "X-CSRF-Token"
_SAFE_BROWSER_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_AUTH_AUDIT_LOGGER = logging.getLogger("docmind_api.auth.audit")


class AuthenticationRequiredError(ApplicationError):
    """Raised when a protected endpoint receives no valid actor."""

    def __init__(self) -> None:
        super().__init__(
            code="AUTHENTICATION_REQUIRED",
            message="Authentication is required.",
            status_code=401,
        )


class PermissionDeniedError(ApplicationError):
    """Raised when an actor lacks permissions required by an endpoint."""

    def __init__(self, required_permissions: frozenset[Permission]) -> None:
        is_document_delete = required_permissions == frozenset({Permission.DOCUMENTS_DELETE})
        super().__init__(
            code="DOCUMENT_DELETE_FORBIDDEN" if is_document_delete else "PERMISSION_DENIED",
            message=(
                "Permanent document deletion is not allowed."
                if is_document_delete
                else "Permission denied."
            ),
            status_code=403,
            details={
                "required_permissions": sorted(
                    permission.value for permission in required_permissions
                ),
            },
        )


class BrowserOriginRejectedError(ApplicationError):
    """Raised when a cookie-authenticated unsafe request comes from an untrusted origin."""

    def __init__(self) -> None:
        super().__init__(
            code="UNTRUSTED_BROWSER_ORIGIN",
            message="Request origin is not allowed.",
            status_code=403,
        )


class CsrfTokenRequiredError(ApplicationError):
    """Raised when an unsafe cookie-authenticated request omits the CSRF header."""

    def __init__(self) -> None:
        super().__init__(
            code="CSRF_TOKEN_REQUIRED",
            message="CSRF token is required.",
            status_code=403,
        )


class CsrfTokenRejectedError(ApplicationError):
    """Raised when an unsafe cookie-authenticated request sends an invalid CSRF token."""

    def __init__(self) -> None:
        super().__init__(
            code="CSRF_TOKEN_REJECTED",
            message="CSRF token is invalid.",
            status_code=403,
        )


def get_actor_resolver() -> ActorResolver:
    """Fail closed until bootstrap wires the configured actor resolver."""

    raise AuthenticationRequiredError()


async def require_authenticated(
    request: Request,
    actor_resolver: Annotated[ActorResolver, Depends(get_actor_resolver)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    session_cookie: Annotated[str | None, Cookie(alias=DOCMIND_SESSION_COOKIE)] = None,
) -> AuthenticatedActor:
    """Return the authenticated actor or fail with 401."""

    return await _resolve_authenticated_actor(
        request=request,
        actor_resolver=actor_resolver,
        authorization=authorization,
        session_id=session_cookie,
        required_permissions=frozenset(),
    )


def require_unsafe_browser_request_protection(
    allowed_origins: tuple[str, ...],
) -> Callable[..., object]:
    """Return a dependency that protects unsafe browser requests from CSRF."""

    normalized_allowed_origins = frozenset(
        normalized_origin
        for origin in allowed_origins
        if (normalized_origin := _normalize_origin(origin)) is not None
    )

    def dependency(
        request: Request,
        origin: Annotated[str | None, Header(alias="Origin")] = None,
        referer: Annotated[str | None, Header(alias="Referer")] = None,
    ) -> None:
        _require_allowed_unsafe_origin(
            request=request,
            origin=origin,
            referer=referer,
            normalized_allowed_origins=normalized_allowed_origins,
        )

    return dependency


def require_cookie_csrf_protection(
    allowed_origins: tuple[str, ...],
    csrf_token_validator_dependency: Callable[..., CsrfTokenValidator],
) -> Callable[..., Awaitable[None]]:
    """Return a dependency that validates origin and CSRF for cookie auth."""

    normalized_allowed_origins = frozenset(
        normalized_origin
        for origin in allowed_origins
        if (normalized_origin := _normalize_origin(origin)) is not None
    )

    async def dependency(
        request: Request,
        csrf_token_validator: Annotated[
            CsrfTokenValidator,
            Depends(csrf_token_validator_dependency),
        ],
        origin: Annotated[str | None, Header(alias="Origin")] = None,
        referer: Annotated[str | None, Header(alias="Referer")] = None,
        session_cookie: Annotated[str | None, Cookie(alias=DOCMIND_SESSION_COOKIE)] = None,
        csrf_token: Annotated[str | None, Header(alias=CSRF_HEADER)] = None,
    ) -> None:
        _require_allowed_unsafe_origin(
            request=request,
            origin=origin,
            referer=referer,
            normalized_allowed_origins=normalized_allowed_origins,
        )
        session_id_value = session_cookie.strip() if session_cookie is not None else ""
        if request.method.upper() in _SAFE_BROWSER_METHODS or not session_id_value:
            return

        active_session = await csrf_token_validator.resolve_session(
            ResolveUserSessionCommand(
                token=OpaqueSessionToken(session_id_value),
                touch_last_seen=False,
            ),
        )
        if active_session is None:
            return

        csrf_token_value = csrf_token.strip() if csrf_token is not None else ""
        if not csrf_token_value:
            raise CsrfTokenRequiredError()

        is_valid = await csrf_token_validator.validate_csrf_token(
            ValidateCsrfTokenCommand(
                session_token=OpaqueSessionToken(session_id_value),
                csrf_token=OpaqueCsrfToken(csrf_token_value),
            ),
        )
        if not is_valid:
            raise CsrfTokenRejectedError()

    return dependency


def require_trusted_browser_origin(
    allowed_origins: tuple[str, ...],
) -> Callable[..., object]:
    """Return the legacy dependency for unsafe browser origin protection."""

    return require_unsafe_browser_request_protection(allowed_origins)


def require_permissions(
    *required_permissions: Permission,
) -> Callable[..., Awaitable[AuthenticatedActor]]:
    """Require an authenticated actor with all listed permissions."""

    required = frozenset(required_permissions)

    async def dependency(
        request: Request,
        actor_resolver: Annotated[ActorResolver, Depends(get_actor_resolver)],
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
        session_cookie: Annotated[str | None, Cookie(alias=DOCMIND_SESSION_COOKIE)] = None,
    ) -> AuthenticatedActor:
        actor = await _resolve_authenticated_actor(
            request=request,
            actor_resolver=actor_resolver,
            authorization=authorization,
            session_id=session_cookie,
            required_permissions=required,
        )
        missing_permissions = frozenset(required - actor.permissions)
        if missing_permissions:
            _log_permission_denied(
                actor=actor,
                required_permissions=required,
                missing_permissions=missing_permissions,
            )
            raise PermissionDeniedError(required_permissions=required)

        return actor

    return dependency


async def _resolve_authenticated_actor(
    *,
    request: Request,
    actor_resolver: ActorResolver,
    authorization: str | None,
    session_id: str | None,
    required_permissions: frozenset[Permission],
) -> AuthenticatedActor:
    auth_context = get_auth_request_context(request)
    if auth_context is not None:
        if auth_context.actor is None:
            _log_authentication_required(
                authorization_present=auth_context.authorization_present,
                browser_session_present=auth_context.browser_session_present,
                required_permissions=required_permissions,
            )
            raise AuthenticationRequiredError()

        return auth_context.actor

    actor = await actor_resolver.resolve_actor(
        ActorCredentials(
            authorization=authorization,
            session_id=session_id,
        )
    )
    if actor is None:
        _log_authentication_required(
            authorization_present=_has_value(authorization),
            browser_session_present=_has_value(session_id),
            required_permissions=required_permissions,
        )
        raise AuthenticationRequiredError()

    return actor


def _log_authentication_required(
    *,
    authorization_present: bool,
    browser_session_present: bool,
    required_permissions: frozenset[Permission],
) -> None:
    _AUTH_AUDIT_LOGGER.warning(
        "API authorization denied.",
        extra={
            "auth_boundary": "api_dependency",
            "auth_decision": "deny",
            "auth_denial_reason": "actor_not_resolved",
            "actor_id": None,
            "auth_provider": None,
            "required_permissions": _permission_values(required_permissions),
            "correlation_id": get_correlation_id(),
            "authn_header_present": authorization_present,
            "browser_session_present": browser_session_present,
        },
    )


def _log_permission_denied(
    *,
    actor: AuthenticatedActor,
    required_permissions: frozenset[Permission],
    missing_permissions: frozenset[Permission],
) -> None:
    _AUTH_AUDIT_LOGGER.warning(
        "API authorization denied.",
        extra={
            "auth_boundary": "api_dependency",
            "auth_decision": "deny",
            "auth_denial_reason": "missing_permissions",
            "actor_id": actor.actor_id,
            "auth_provider": actor.provider.value,
            "required_permissions": _permission_values(required_permissions),
            "missing_permissions": _permission_values(missing_permissions),
            "correlation_id": get_correlation_id(),
        },
    )


def _permission_values(permissions: frozenset[Permission]) -> tuple[str, ...]:
    return tuple(sorted(permission.value for permission in permissions))


def _has_value(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _request_origin(*, origin: str | None, referer: str | None) -> str | None:
    if origin is not None:
        return _normalize_origin(origin)

    if referer is None:
        return None

    return _normalize_origin(referer)


def _require_allowed_unsafe_origin(
    *,
    request: Request,
    origin: str | None,
    referer: str | None,
    normalized_allowed_origins: frozenset[str],
) -> None:
    if request.method.upper() in _SAFE_BROWSER_METHODS:
        return

    request_origin = _request_origin(origin=origin, referer=referer)
    if request_origin is None or request_origin not in normalized_allowed_origins:
        raise BrowserOriginRejectedError()


def _normalize_origin(value: str) -> str | None:
    stripped_value = value.strip()
    if not stripped_value or stripped_value == "null":
        return None

    parsed_value = urlsplit(stripped_value)
    if not parsed_value.scheme or not parsed_value.netloc:
        return None

    return urlunsplit(
        (
            parsed_value.scheme.lower(),
            parsed_value.netloc.lower(),
            "",
            "",
            "",
        )
    )
