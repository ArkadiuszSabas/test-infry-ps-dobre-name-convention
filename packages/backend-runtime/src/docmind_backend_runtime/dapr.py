"""Service-neutral Dapr sidecar client helpers."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from os import environ
from typing import Any
from urllib.parse import quote

import httpx

from docmind_backend_runtime.environment import get_environment_variable, load_environment_files

_DAPR_HTTP_ENDPOINT_ENV = "DAPR_HTTP_ENDPOINT"
_DAPR_RUNTIME_HOST_ENV = "DAPR_RUNTIME_HOST"
_DAPR_HTTP_PORT_ENV = "DAPR_HTTP_PORT"
_DOCMIND_DAPR_RUNTIME_HOST_ENV = "DOCMIND_DAPR_RUNTIME_HOST"
_DOCMIND_DAPR_HTTP_TIMEOUT_ENV = "DOCMIND_DAPR_HTTP_TIMEOUT_SECONDS"


@dataclass(frozen=True, slots=True)
class DaprClientSettings:
    """Settings required to talk to one local Dapr sidecar."""

    app_id: str
    http_endpoint: str
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class DaprInvocationResponse:
    """Transport-neutral response returned from Dapr service invocation."""

    status_code: int
    headers: Mapping[str, str]
    content: bytes

    @property
    def text(self) -> str:
        """Decode response bytes using UTF-8."""

        return self.content.decode("utf-8")

    def json(self) -> Any:
        """Decode response content as JSON."""

        return json.loads(self.text)


class DaprClientError(RuntimeError):
    """Raised when communication with the local Dapr sidecar fails."""


class DaprClientTimeoutError(DaprClientError):
    """Raised when a Dapr request times out with an indeterminate remote outcome."""


class DaprHttpClient:
    """Small async HTTP client for Dapr sidecar APIs."""

    def __init__(
        self,
        settings: DaprClientSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client

    @property
    def app_id(self) -> str:
        """Return the local app ID this client is configured for."""

        return self._settings.app_id

    async def invoke_method(
        self,
        target_app_id: str,
        method_name: str,
        *,
        http_method: str = "GET",
        headers: Mapping[str, str] | None = None,
        json_body: Any | None = None,
        content: bytes | str | None = None,
    ) -> DaprInvocationResponse:
        """Invoke an HTTP method on another Dapr-enabled app."""

        path = _service_invocation_path(target_app_id=target_app_id, method_name=method_name)

        try:
            async with self._client() as client:
                response = await client.request(
                    http_method.upper(),
                    path,
                    headers=headers,
                    json=json_body,
                    content=content,
                )
        except httpx.TimeoutException as error:
            raise DaprClientTimeoutError(
                f"Dapr sidecar request timed out for app '{target_app_id}' method '{method_name}'.",
            ) from error
        except httpx.HTTPError as error:
            raise DaprClientError(
                f"Dapr sidecar request failed for app '{target_app_id}' method '{method_name}'.",
            ) from error

        return DaprInvocationResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
        )

    async def publish_event(
        self,
        pubsub_name: str,
        topic_name: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Any,
    ) -> DaprInvocationResponse:
        """Publish one event through a Dapr pub/sub component."""

        path = _publish_event_path(pubsub_name=pubsub_name, topic_name=topic_name)

        try:
            async with self._client() as client:
                response = await client.post(path, headers=headers, json=json_body)
        except httpx.TimeoutException as error:
            raise DaprClientTimeoutError(
                f"Dapr publish request timed out for pubsub '{pubsub_name}' topic '{topic_name}'.",
            ) from error
        except httpx.HTTPError as error:
            raise DaprClientError(
                f"Dapr publish request failed for pubsub '{pubsub_name}' topic '{topic_name}'.",
            ) from error

        return DaprInvocationResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
        )

    @asynccontextmanager
    async def _client(self) -> AsyncGenerator[httpx.AsyncClient]:
        if self._http_client is not None:
            yield self._http_client
            return

        async with httpx.AsyncClient(
            base_url=self._settings.http_endpoint,
            timeout=self._settings.timeout_seconds,
        ) as client:
            yield client


def load_dapr_client_settings(
    *,
    app_id: str,
    http_endpoint_env: str | None = None,
    http_port_env: str | None = None,
    runtime_host_env: str = _DOCMIND_DAPR_RUNTIME_HOST_ENV,
    timeout_env: str = _DOCMIND_DAPR_HTTP_TIMEOUT_ENV,
    allow_platform_endpoint: bool = True,
) -> DaprClientSettings:
    """Load Dapr sidecar client settings from environment variables."""

    platform_environment = _read_platform_dapr_environment()
    load_environment_files()
    normalized_app_id = _normalize_app_id(app_id)
    http_endpoint = _load_http_endpoint(
        http_endpoint_env=http_endpoint_env,
        http_port_env=http_port_env,
        runtime_host_env=runtime_host_env,
        allow_platform_endpoint=allow_platform_endpoint,
        platform_environment=platform_environment,
    )

    return DaprClientSettings(
        app_id=normalized_app_id,
        http_endpoint=http_endpoint,
        timeout_seconds=_env_required_float(timeout_env),
    )


def create_dapr_client(settings: DaprClientSettings) -> DaprHttpClient:
    """Create the default Dapr HTTP client for a service."""

    return DaprHttpClient(settings)


def build_dapr_service_invocation_url(
    *,
    http_endpoint: str,
    target_app_id: str,
    method_name: str,
) -> str:
    """Build the full Dapr sidecar URL for one service invocation."""

    endpoint = _normalize_http_endpoint(http_endpoint)
    path = _service_invocation_path(target_app_id=target_app_id, method_name=method_name)

    return f"{endpoint}{path}"


def build_dapr_publish_url(
    *,
    http_endpoint: str,
    pubsub_name: str,
    topic_name: str,
) -> str:
    """Build the full Dapr sidecar URL for one pub/sub publish request."""

    endpoint = _normalize_http_endpoint(http_endpoint)
    path = _publish_event_path(pubsub_name=pubsub_name, topic_name=topic_name)

    return f"{endpoint}{path}"


def _load_http_endpoint(
    *,
    http_endpoint_env: str | None,
    http_port_env: str | None,
    runtime_host_env: str,
    allow_platform_endpoint: bool,
    platform_environment: Mapping[str, str],
) -> str:
    if allow_platform_endpoint:
        explicit_endpoint = _platform_env_optional_str(
            _DAPR_HTTP_ENDPOINT_ENV,
            platform_environment,
        )
        if explicit_endpoint is not None:
            return _normalize_http_endpoint(explicit_endpoint)

    if http_endpoint_env is not None:
        service_endpoint = _env_optional_str(http_endpoint_env)
        if service_endpoint is not None:
            return _normalize_http_endpoint(service_endpoint)

    platform_port_env = _DAPR_HTTP_PORT_ENV if allow_platform_endpoint else None
    port = _first_dapr_http_port(
        platform_port_env,
        http_port_env,
        platform_environment,
    )
    if port is None:
        endpoint_options = _format_env_options(
            _DAPR_HTTP_ENDPOINT_ENV if allow_platform_endpoint else None,
            http_endpoint_env,
        )
        port_options = _format_env_options(platform_port_env, http_port_env)
        host_options = _format_env_options(_DAPR_RUNTIME_HOST_ENV, runtime_host_env)
        raise RuntimeError(
            "Missing Dapr HTTP endpoint configuration. Set "
            f"{endpoint_options}, or set {port_options} with {host_options}.",
        )

    host = _first_dapr_runtime_host(
        _DAPR_RUNTIME_HOST_ENV,
        runtime_host_env,
        platform_environment,
    )
    if host is None:
        port_options = _format_env_options(platform_port_env, http_port_env)
        host_options = _format_env_options(_DAPR_RUNTIME_HOST_ENV, runtime_host_env)
        raise RuntimeError(
            "Missing Dapr runtime host configuration. Set "
            f"{host_options} when using {port_options}.",
        )

    return _normalize_http_endpoint(f"http://{host}:{port}")


def _service_invocation_path(*, target_app_id: str, method_name: str) -> str:
    normalized_app_id = _normalize_app_id(target_app_id)
    normalized_method = method_name.strip("/")
    if not normalized_method:
        raise ValueError("Dapr invocation method_name must not be blank.")

    return (
        f"/v1.0/invoke/{quote(normalized_app_id, safe='')}/method/"
        f"{quote(normalized_method, safe='/')}"
    )


def _publish_event_path(*, pubsub_name: str, topic_name: str) -> str:
    normalized_pubsub_name = _require_non_blank("Dapr pubsub_name", pubsub_name)
    normalized_topic_name = _require_non_blank("Dapr topic_name", topic_name)

    return (
        f"/v1.0/publish/{quote(normalized_pubsub_name, safe='')}/"
        f"{quote(normalized_topic_name, safe='')}"
    )


def _normalize_app_id(app_id: str) -> str:
    normalized_app_id = app_id.strip()
    if not normalized_app_id:
        raise ValueError("Dapr app_id must not be blank.")
    if "." in normalized_app_id:
        raise ValueError("Dapr app_id must not contain dots.")

    return normalized_app_id


def _normalize_http_endpoint(value: str) -> str:
    endpoint = value.strip().rstrip("/")
    if not endpoint.startswith(("http://", "https://")):
        raise ValueError("Dapr HTTP endpoint must start with http:// or https://.")

    return endpoint


def _require_non_blank(name: str, value: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{name} must not be blank.")

    return normalized_value


def _env_optional_str(name: str) -> str | None:
    return get_environment_variable(name)


def _read_platform_dapr_environment() -> Mapping[str, str]:
    values: dict[str, str] = {}
    for name in (_DAPR_HTTP_ENDPOINT_ENV, _DAPR_RUNTIME_HOST_ENV, _DAPR_HTTP_PORT_ENV):
        value = environ.get(name)
        if value is None:
            continue

        stripped_value = value.strip()
        if stripped_value:
            values[name] = stripped_value

    return values


def _platform_env_optional_str(
    name: str,
    platform_environment: Mapping[str, str],
) -> str | None:
    return platform_environment.get(name)


def _first_dapr_runtime_host(
    platform_name: str,
    docmind_name: str,
    platform_environment: Mapping[str, str],
) -> str | None:
    platform_value = _platform_env_optional_str(platform_name, platform_environment)
    if platform_value is not None:
        return platform_value

    return _env_optional_str(docmind_name)


def _first_dapr_http_port(
    platform_name: str | None,
    docmind_name: str | None,
    platform_environment: Mapping[str, str],
) -> int | None:
    if platform_name is not None:
        platform_value = _platform_env_optional_str(platform_name, platform_environment)
        if platform_value is not None:
            return _parse_tcp_port(platform_name, platform_value)

    if docmind_name is None:
        return None

    value = _env_optional_str(docmind_name)
    if value is None:
        return None

    return _parse_tcp_port(docmind_name, value)


def _parse_tcp_port(name: str, value: str) -> int:
    try:
        port = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer value.") from error
    if port < 1 or port > 65535:
        raise ValueError(f"{name} must be a TCP port between 1 and 65535.")

    return port


def _env_required_float(name: str) -> float:
    value = _env_optional_str(name)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")

    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a number.") from error


def _format_env_options(*names: str | None) -> str:
    return " or ".join(name for name in names if name is not None)
