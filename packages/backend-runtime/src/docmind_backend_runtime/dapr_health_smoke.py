"""Dapr service invocation health smoke runner."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from docmind_backend_runtime.correlation import CORRELATION_ID_HEADER
from docmind_backend_runtime.dapr import (
    DaprClientError,
    DaprClientSettings,
    DaprHttpClient,
    DaprInvocationResponse,
    build_dapr_service_invocation_url,
    create_dapr_client,
    load_dapr_client_settings,
)

DEFAULT_HEALTH_PATHS = ("/health/ready",)
DEFAULT_CORRELATION_ID = "docmind-dapr-health-smoke"

type DaprClientFactory = Callable[[DaprClientSettings], DaprHttpClient]


@dataclass(frozen=True, slots=True)
class DaprHealthSmokeSource:
    """One Dapr sidecar used as the source of invocation calls."""

    name: str
    app_id: str
    http_endpoint_env: str | None = None
    http_port_env: str | None = None

    def __post_init__(self) -> None:
        _require_non_blank("source name", self.name)
        _require_non_blank("source app_id", self.app_id)


@dataclass(frozen=True, slots=True)
class DaprHealthSmokeTarget:
    """One Dapr-enabled target application."""

    name: str
    app_id: str

    def __post_init__(self) -> None:
        _require_non_blank("target name", self.name)
        _require_non_blank("target app_id", self.app_id)


@dataclass(frozen=True, slots=True)
class DaprHealthSmokeInvocation:
    """One health endpoint invocation to execute through Dapr."""

    source: DaprHealthSmokeSource
    target: DaprHealthSmokeTarget
    path: str

    def __post_init__(self) -> None:
        _require_non_blank("health path", self.path)


@dataclass(frozen=True, slots=True)
class DaprHealthSmokeResult:
    """Result of one Dapr health smoke invocation."""

    source_name: str
    source_app_id: str
    target_name: str
    target_app_id: str
    path: str
    status_code: int | None
    response_correlation_id: str | None
    health_status: str | None
    failure: str | None = None
    invocation_url: str | None = None

    @property
    def passed(self) -> bool:
        """Return whether this invocation satisfied the smoke assertions."""

        return self.failure is None

    def format_line(self) -> str:
        """Return a compact human-readable result line."""

        prefix = "OK" if self.passed else "FAIL"
        status = "transport-error" if self.status_code is None else str(self.status_code)
        detail = (
            f"[{prefix}] {self.source_name} -> {self.target_name} {self.path} "
            f"status={status} correlation={self.response_correlation_id or '<missing>'}"
        )
        if self.failure is not None:
            return f"{detail} :: {self.failure}"

        return detail


@dataclass(frozen=True, slots=True)
class DaprHealthSmokeReport:
    """Aggregated Dapr health smoke result."""

    results: tuple[DaprHealthSmokeResult, ...]

    @property
    def passed(self) -> bool:
        """Return whether every invocation passed."""

        return all(result.passed for result in self.results)

    @property
    def failures(self) -> tuple[DaprHealthSmokeResult, ...]:
        """Return failed invocation results."""

        return tuple(result for result in self.results if not result.passed)

    def format_lines(self) -> tuple[str, ...]:
        """Return result lines for diagnostics."""

        return tuple(result.format_line() for result in self.results)


class DaprHealthSmokeError(RuntimeError):
    """Raised when one or more Dapr health smoke checks fail."""

    def __init__(self, report: DaprHealthSmokeReport) -> None:
        self.report = report
        failure_lines = "\n".join(result.format_line() for result in report.failures)
        super().__init__(f"Dapr health smoke failed:\n{failure_lines}")


def docmind_local_dapr_health_smoke_sources() -> tuple[DaprHealthSmokeSource, ...]:
    """Return the local DocMind.ai Dapr sidecar topology."""

    return (
        DaprHealthSmokeSource(
            name="api",
            app_id="docmind-api",
            http_endpoint_env="DOCMIND_API_DAPR_HTTP_ENDPOINT",
            http_port_env="DOCMIND_API_DAPR_HTTP_PORT",
        ),
        DaprHealthSmokeSource(
            name="llmmagic",
            app_id="docmind-llmmagic",
            http_endpoint_env="DOCMIND_LLMMAGIC_DAPR_HTTP_ENDPOINT",
            http_port_env="DOCMIND_LLMMAGIC_DAPR_HTTP_PORT",
        ),
        DaprHealthSmokeSource(
            name="worker",
            app_id="docmind-worker",
            http_endpoint_env="DOCMIND_WORKER_DAPR_HTTP_ENDPOINT",
            http_port_env="DOCMIND_WORKER_DAPR_HTTP_PORT",
        ),
    )


def build_dapr_health_smoke_matrix(
    sources: Sequence[DaprHealthSmokeSource],
    *,
    health_paths: Sequence[str] = DEFAULT_HEALTH_PATHS,
) -> tuple[DaprHealthSmokeInvocation, ...]:
    """Build full-mesh health invocations for every source-target pair."""

    _require_at_least_two_sources(sources)
    normalized_paths = _normalize_health_paths(health_paths)
    invocations: list[DaprHealthSmokeInvocation] = []

    for source in sources:
        for target_source in sources:
            if target_source.app_id == source.app_id:
                continue
            target = DaprHealthSmokeTarget(name=target_source.name, app_id=target_source.app_id)
            invocations.extend(
                DaprHealthSmokeInvocation(source=source, target=target, path=path)
                for path in normalized_paths
            )

    return tuple(invocations)


async def run_dapr_health_smoke(
    invocations: Sequence[DaprHealthSmokeInvocation],
    *,
    correlation_id: str = DEFAULT_CORRELATION_ID,
    client_factory: DaprClientFactory = create_dapr_client,
) -> DaprHealthSmokeReport:
    """Run Dapr health invocations and raise when any check fails."""

    report = await collect_dapr_health_smoke(
        invocations,
        correlation_id=correlation_id,
        client_factory=client_factory,
    )
    if not report.passed:
        raise DaprHealthSmokeError(report)

    return report


async def collect_dapr_health_smoke(
    invocations: Sequence[DaprHealthSmokeInvocation],
    *,
    correlation_id: str = DEFAULT_CORRELATION_ID,
    client_factory: DaprClientFactory = create_dapr_client,
) -> DaprHealthSmokeReport:
    """Run Dapr health invocations and return every result without raising on failures."""

    if not invocations:
        raise ValueError("At least one Dapr health smoke invocation is required.")
    _require_non_blank("correlation_id", correlation_id)

    results = [
        await check_dapr_health_invocation(
            invocation,
            correlation_id=correlation_id,
            client_factory=client_factory,
        )
        for invocation in invocations
    ]

    return DaprHealthSmokeReport(results=tuple(results))


async def check_dapr_health_invocation(
    invocation: DaprHealthSmokeInvocation,
    *,
    correlation_id: str,
    client_factory: DaprClientFactory,
) -> DaprHealthSmokeResult:
    """Run one Dapr health invocation and return a structured result."""

    try:
        settings = load_dapr_client_settings(
            app_id=invocation.source.app_id,
            http_endpoint_env=invocation.source.http_endpoint_env,
            http_port_env=invocation.source.http_port_env,
            allow_platform_endpoint=False,
        )
    except (RuntimeError, ValueError) as error:
        return _configuration_error_result(invocation, error)

    invocation_url = build_dapr_service_invocation_url(
        http_endpoint=settings.http_endpoint,
        target_app_id=invocation.target.app_id,
        method_name=invocation.path,
    )
    client = client_factory(settings)

    try:
        response = await client.invoke_method(
            invocation.target.app_id,
            invocation.path,
            headers={CORRELATION_ID_HEADER: correlation_id},
        )
    except DaprClientError as error:
        return _transport_error_result(invocation, error, invocation_url=invocation_url)

    failure = _response_failure(
        response,
        expected_correlation_id=correlation_id,
    )
    return DaprHealthSmokeResult(
        source_name=invocation.source.name,
        source_app_id=invocation.source.app_id,
        target_name=invocation.target.name,
        target_app_id=invocation.target.app_id,
        path=invocation.path,
        status_code=response.status_code,
        response_correlation_id=_header_value(response.headers, CORRELATION_ID_HEADER),
        health_status=_health_status(response),
        failure=failure,
        invocation_url=invocation_url,
    )


def _configuration_error_result(
    invocation: DaprHealthSmokeInvocation,
    error: RuntimeError | ValueError,
) -> DaprHealthSmokeResult:
    return DaprHealthSmokeResult(
        source_name=invocation.source.name,
        source_app_id=invocation.source.app_id,
        target_name=invocation.target.name,
        target_app_id=invocation.target.app_id,
        path=invocation.path,
        status_code=None,
        response_correlation_id=None,
        health_status=None,
        failure=f"source sidecar '{invocation.source.app_id}' configuration failed: {error}",
    )


def _transport_error_result(
    invocation: DaprHealthSmokeInvocation,
    error: DaprClientError,
    *,
    invocation_url: str,
) -> DaprHealthSmokeResult:
    return DaprHealthSmokeResult(
        source_name=invocation.source.name,
        source_app_id=invocation.source.app_id,
        target_name=invocation.target.name,
        target_app_id=invocation.target.app_id,
        path=invocation.path,
        status_code=None,
        response_correlation_id=None,
        health_status=None,
        failure=(
            f"source sidecar '{invocation.source.app_id}' failed invoking "
            f"target '{invocation.target.app_id}': {error}"
        ),
        invocation_url=invocation_url,
    )


def _response_failure(
    response: DaprInvocationResponse,
    *,
    expected_correlation_id: str,
) -> str | None:
    failures: list[str] = []
    if response.status_code != 200:
        failures.append(f"expected HTTP 200, got {response.status_code}")

    actual_correlation_id = _header_value(response.headers, CORRELATION_ID_HEADER)
    if actual_correlation_id != expected_correlation_id:
        failures.append(
            f"expected {CORRELATION_ID_HEADER}={expected_correlation_id}, "
            f"got {actual_correlation_id or '<missing>'}",
        )

    health_status = _health_status(response)
    if health_status != "healthy":
        failures.append(f"expected health status healthy, got {health_status or '<missing>'}")

    return "; ".join(failures) if failures else None


def _health_status(response: DaprInvocationResponse) -> str | None:
    try:
        payload: object = response.json()
    except ValueError, UnicodeError:
        return None

    if not isinstance(payload, Mapping):
        return None

    payload_mapping = cast(Mapping[str, object], payload)
    data = payload_mapping.get("data")
    if not isinstance(data, Mapping):
        return None

    data_mapping = cast(Mapping[str, object], data)
    status = data_mapping.get("status")
    return status if isinstance(status, str) else None


def _header_value(headers: Mapping[str, str], name: str) -> str | None:
    normalized_name = name.lower()
    for header_name, header_value in headers.items():
        if header_name.lower() == normalized_name:
            return header_value

    return None


def _normalize_health_paths(health_paths: Sequence[str]) -> tuple[str, ...]:
    normalized_paths = tuple(path.strip() for path in health_paths if path.strip())
    if not normalized_paths:
        raise ValueError("At least one health path is required.")

    return normalized_paths


def _require_at_least_two_sources(sources: Sequence[DaprHealthSmokeSource]) -> None:
    if len(sources) < 2:
        raise ValueError("At least two Dapr health smoke sources are required.")

    app_ids = [source.app_id for source in sources]
    duplicate_app_ids = {app_id for app_id in app_ids if app_ids.count(app_id) > 1}
    if duplicate_app_ids:
        duplicates = ", ".join(sorted(duplicate_app_ids))
        raise ValueError(f"Dapr health smoke sources must have unique app IDs: {duplicates}")


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be blank.")
