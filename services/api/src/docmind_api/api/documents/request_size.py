"""Request body size guard for document content endpoints."""

from http import HTTPStatus
from typing import cast

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_DOCUMENT_INGEST_PATH = "/documents/ingest"
_DOCUMENT_MANUAL_UPLOAD_PATH = "/documents/manual-upload"
_CONNECTOR_PATH_PREFIX = "/connectors/"
_DOCUMENT_CONTENT_PATHS = frozenset({_DOCUMENT_INGEST_PATH, _DOCUMENT_MANUAL_UPLOAD_PATH})
_DEFAULT_MANUAL_UPLOAD_REQUEST_OVERHEAD_BYTES = 1024 * 1024


class DocumentRequestTooLargeError(Exception):
    """Raised when a guarded request body exceeds the configured limit."""


class DocumentContentTooLargeError(Exception):
    """Raised when a guarded document content body exceeds the configured limit."""


class DocumentContentRequestSizeLimitMiddleware:
    """Reject oversized document content request bodies before route parsing."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_content_bytes: int,
        max_request_bytes: int,
        manual_upload_request_overhead_bytes: int = (_DEFAULT_MANUAL_UPLOAD_REQUEST_OVERHEAD_BYTES),
    ) -> None:
        self._app = app
        self._max_content_bytes = max_content_bytes
        self._max_request_bytes = max_request_bytes
        self._max_manual_upload_request_bytes = (
            max_content_bytes + manual_upload_request_overhead_bytes
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._should_guard(scope):
            await self._app(scope, receive, send)
            return

        content_length = _content_length(scope)
        if content_length is not None and content_length > self._max_request_bytes:
            await self._reject(scope, receive, send)
            return
        if (
            content_length is not None
            and scope.get("path") == _DOCUMENT_MANUAL_UPLOAD_PATH
            and content_length > self._max_manual_upload_request_bytes
        ):
            await self._reject_manual_upload_content(scope, receive, send)
            return

        received_bytes = 0
        path = scope.get("path")
        manual_upload_stream_limit = (
            self._max_manual_upload_request_bytes if path == _DOCUMENT_MANUAL_UPLOAD_PATH else None
        )

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] != "http.request":
                return message

            body = cast(bytes, message.get("body", b""))
            received_bytes += len(body)
            if (
                manual_upload_stream_limit is not None
                and received_bytes > manual_upload_stream_limit
            ):
                raise DocumentContentTooLargeError()
            if received_bytes > self._max_request_bytes:
                raise DocumentRequestTooLargeError()

            return message

        try:
            await self._app(scope, limited_receive, send)
        except DocumentContentTooLargeError:
            await self._reject_manual_upload_content(scope, receive, send)
        except DocumentRequestTooLargeError:
            await self._reject(scope, receive, send)

    def _should_guard(self, scope: Scope) -> bool:
        return (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and (
                scope.get("path") in _DOCUMENT_CONTENT_PATHS
                or str(scope.get("path", "")).startswith(_CONNECTOR_PATH_PREFIX)
            )
        )

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            content={
                "error": {
                    "code": "DOCUMENT_REQUEST_TOO_LARGE",
                    "message": "Document request exceeds the configured maximum size.",
                    "details": {"max_request_bytes": self._max_request_bytes},
                },
            },
        )
        await response(scope, receive, send)

    async def _reject_manual_upload_content(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        response = JSONResponse(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            content={
                "error": {
                    "code": "DOCUMENT_CONTENT_TOO_LARGE",
                    "message": "Document content exceeds the configured maximum size.",
                    "details": {"max_content_bytes": self._max_content_bytes},
                },
            },
        )
        await response(scope, receive, send)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope["headers"]:
        if name != b"content-length":
            continue
        try:
            return int(value.decode("ascii"))
        except ValueError:
            return None

    return None
