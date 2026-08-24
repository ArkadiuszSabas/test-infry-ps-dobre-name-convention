"""Authenticated HTTP transport and safe Graph failure classification."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Mapping
from contextlib import asynccontextmanager

import httpx

from docmind_integrations.sharepoint._payloads import mapping, object_list
from docmind_integrations.sharepoint.errors import (
    GraphAuthenticationError,
    GraphAuthorizationError,
    GraphConflictError,
    GraphProtocolError,
    GraphRateLimitError,
    GraphResourceNotFoundError,
    GraphServiceUnavailableError,
    GraphTimeoutError,
)
from docmind_integrations.sharepoint.tokens import GRAPH_DEFAULT_SCOPE, AccessTokenProvider

_GRAPH_BASE_URL = "https://graph.microsoft.com"
_GRAPH_API_PREFIX = "/v1.0"


class GraphTransport:
    """Internal authenticated transport shared by all client operations."""

    def __init__(
        self,
        token_provider: AccessTokenProvider,
        *,
        http_client: httpx.AsyncClient | None,
        timeout_seconds: float,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")
        self._token_provider = token_provider
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

    async def list_values(self, endpoint: str, *, operation: str) -> list[Mapping[str, object]]:
        values: list[Mapping[str, object]] = []
        next_endpoint: str | None = endpoint
        while next_endpoint is not None:
            payload = await self.request_json("GET", next_endpoint, operation=operation)
            values.extend(self.response_values(payload, "collection response"))
            next_endpoint = _next_graph_endpoint(payload.get("@odata.nextLink"))
        return values

    def response_values(
        self, payload: Mapping[str, object], name: str
    ) -> list[Mapping[str, object]]:
        return [mapping(value, name) for value in object_list(payload.get("value"), name)]

    async def request_json(
        self,
        method: str,
        endpoint: str,
        *,
        operation: str,
        content: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        response = await self._send(method, endpoint, operation, content, headers, json_body)
        try:
            return mapping(response.json(), "response")
        except ValueError, GraphProtocolError:
            raise GraphProtocolError(
                f"Microsoft Graph returned an invalid response while attempting to {operation}."
            ) from None

    async def request_content(self, method: str, endpoint: str, *, operation: str) -> bytes:
        return (await self._send(method, endpoint, operation, None, None, None)).content

    async def request_empty(self, method: str, endpoint: str, *, operation: str) -> None:
        await self._send(method, endpoint, operation, None, None, None)

    async def _send(
        self,
        method: str,
        endpoint: str,
        operation: str,
        content: bytes | None,
        headers: Mapping[str, str] | None,
        json_body: Mapping[str, object] | None,
    ) -> httpx.Response:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                token = await self._get_token()
                request_headers = {"Authorization": f"Bearer {token}"}
                if headers is not None:
                    request_headers.update(headers)
                async with self._client() as client:
                    response = await client.request(
                        method,
                        _graph_endpoint(endpoint),
                        headers=request_headers,
                        content=content,
                        json=json_body,
                        follow_redirects=True,
                    )
        except TimeoutError, httpx.TimeoutException:
            raise GraphTimeoutError(
                f"Microsoft Graph timed out while attempting to {operation}."
            ) from None
        except httpx.HTTPError:
            raise GraphServiceUnavailableError(
                f"Microsoft Graph was unavailable while attempting to {operation}."
            ) from None
        _raise_for_status(response, operation)
        return response

    async def _get_token(self) -> str:
        try:
            token = await self._token_provider.get_token(GRAPH_DEFAULT_SCOPE)
        except Exception:
            raise GraphAuthenticationError(
                "Could not acquire a Microsoft Graph access token."
            ) from None
        if not token:
            raise GraphAuthenticationError("Could not acquire a Microsoft Graph access token.")
        return token

    @asynccontextmanager
    async def _client(self) -> AsyncGenerator[httpx.AsyncClient]:
        if self._http_client is not None:
            yield self._http_client
            return
        async with httpx.AsyncClient(
            base_url=_GRAPH_BASE_URL,
            timeout=self._timeout_seconds,
            follow_redirects=True,
        ) as client:
            yield client


def _graph_endpoint(endpoint: str) -> str:
    if endpoint.startswith("https://graph.microsoft.com/v1.0/"):
        return endpoint
    if not endpoint.startswith("/"):
        raise GraphProtocolError("Microsoft Graph returned an invalid pagination link.")
    return f"{_GRAPH_BASE_URL}{_GRAPH_API_PREFIX}{endpoint}"


def _next_graph_endpoint(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.startswith("https://graph.microsoft.com/v1.0/"):
        raise GraphProtocolError("Microsoft Graph returned an invalid pagination link.")
    return value


def _raise_for_status(response: httpx.Response, operation: str) -> None:
    status_code = response.status_code
    if status_code < 400:
        return
    message = f"Microsoft Graph rejected the request while attempting to {operation}."
    if status_code == 401:
        raise GraphAuthenticationError(message)
    if status_code == 403:
        raise GraphAuthorizationError(message)
    if status_code == 404:
        raise GraphResourceNotFoundError(message)
    if status_code == 409:
        raise GraphConflictError(message)
    if status_code == 429:
        raise GraphRateLimitError(message, retry_after_seconds=_retry_after_seconds(response))
    if status_code >= 500:
        raise GraphServiceUnavailableError(message)
    raise GraphProtocolError(message)


def _retry_after_seconds(response: httpx.Response) -> int | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0, int(value))
    except ValueError:
        return None
