"""Request context storage for the current async execution."""

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Runtime context available while handling one request."""

    correlation_id: str
    service_name: str
    environment: str


_request_context: ContextVar[RequestContext | None] = ContextVar(
    "docmind_request_context",
    default=None,
)


def set_request_context(context: RequestContext) -> Token[RequestContext | None]:
    """Store request context and return a token for resetting it."""

    return _request_context.set(context)


def reset_request_context(token: Token[RequestContext | None]) -> None:
    """Reset request context to the previous value."""

    _request_context.reset(token)


def get_request_context() -> RequestContext | None:
    """Return the current request context when code runs inside a request."""

    return _request_context.get()


def get_correlation_id() -> str | None:
    """Return the current correlation id when code runs inside a request."""

    context = get_request_context()
    if context is None:
        return None

    return context.correlation_id
