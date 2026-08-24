"""FastAPI middleware installers."""

import logging
from time import perf_counter

from fastapi import FastAPI
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from docmind_backend_runtime.context import (
    RequestContext,
    reset_request_context,
    set_request_context,
)
from docmind_backend_runtime.correlation import get_or_create_correlation_id
from docmind_backend_runtime.settings import RuntimeSettings

_REQUEST_STATE_KEY = "state"
_CORRELATION_STATE_KEY = "correlation_id"
_REQUEST_LOGGER = logging.getLogger("docmind_backend_runtime.requests")


def install_correlation_id_middleware(app: FastAPI, *, settings: RuntimeSettings) -> None:
    """Install middleware that manages correlation id and request context."""

    app.add_middleware(CorrelationIdMiddleware, settings=settings)


class CorrelationIdMiddleware:
    """ASGI middleware that stores and returns a request correlation id."""

    def __init__(self, app: ASGIApp, *, settings: RuntimeSettings) -> None:
        self._app = app
        self._settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        correlation_id = get_or_create_correlation_id(
            Headers(scope=scope),
            header_name=self._settings.correlation_header_name,
        )
        context = RequestContext(
            correlation_id=correlation_id,
            service_name=self._settings.service_name,
            environment=self._settings.environment,
        )
        token = set_request_context(context)
        # ContextVar is the canonical request context; ASGI state is a Request-native fallback
        # for framework code that still has Request after contextvars are no longer available.
        self._store_correlation_id_in_scope(scope, correlation_id)
        started_at = perf_counter()
        status_code: int | None = None

        async def send_with_correlation_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = MutableHeaders(scope=message)
                headers[self._settings.correlation_header_name] = correlation_id

            await send(message)

        try:
            await self._app(scope, receive, send_with_correlation_id)
        except Exception:
            status_code = status_code or 500
            self._log_request(scope, status_code=status_code, duration_ms=_duration_ms(started_at))
            raise
        else:
            self._log_request(
                scope,
                status_code=status_code or 500,
                duration_ms=_duration_ms(started_at),
            )
        finally:
            reset_request_context(token)

    @staticmethod
    def _store_correlation_id_in_scope(scope: Scope, correlation_id: str) -> None:
        state = scope.setdefault(_REQUEST_STATE_KEY, {})
        if isinstance(state, dict):
            state[_CORRELATION_STATE_KEY] = correlation_id

    def _log_request(self, scope: Scope, *, status_code: int, duration_ms: float) -> None:
        if not self._settings.request_logging_enabled:
            return

        path = _scope_path(scope)
        if _is_excluded_path(path, self._settings.request_logging_excluded_paths):
            return

        level = logging.ERROR if status_code >= 500 else logging.INFO
        _REQUEST_LOGGER.log(
            level,
            "HTTP request completed.",
            extra={
                "http_method": _scope_method(scope),
                "http_path": path,
                "http_status_code": status_code,
                "duration_ms": round(duration_ms, 3),
            },
        )


def _duration_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000


def _scope_path(scope: Scope) -> str:
    path = scope.get("path")
    if isinstance(path, str):
        return path

    return ""


def _scope_method(scope: Scope) -> str:
    method = scope.get("method")
    if isinstance(method, str):
        return method

    return ""


def _is_excluded_path(path: str, excluded_paths: tuple[str, ...]) -> bool:
    normalized_path = path.rstrip("/") or "/"
    return any(normalized_path == excluded_path.rstrip("/") for excluded_path in excluded_paths)
