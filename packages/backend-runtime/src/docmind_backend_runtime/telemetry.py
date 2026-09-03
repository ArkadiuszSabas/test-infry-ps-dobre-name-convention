"""Optional Azure Monitor OpenTelemetry integration."""

from __future__ import annotations

import importlib
import logging
from collections.abc import MutableMapping
from dataclasses import dataclass
from os import environ
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlsplit, urlunsplit

from opentelemetry.sdk.trace import SpanProcessor

from docmind_backend_runtime.azure_logging import (
    AzureMonitorLogFormatter,
    SafeAzureMonitorLogRecordProcessor,
    azure_monitor_attribute_value,
)
from docmind_backend_runtime.logging_sanitization import REDACTED
from docmind_backend_runtime.settings import (
    RuntimeSettings,
    is_placeholder_azure_monitor_connection_string,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

_logger = logging.getLogger("docmind_backend_runtime.telemetry")
_azure_monitor_configured = False
_QUERY_STRING_ATTRIBUTE_NAMES = frozenset(
    {
        "http.target",
        "http.url",
        "url.full",
        "url.path",
    }
)
_REMOVED_SPAN_ATTRIBUTE_NAMES = frozenset({"url.query"})
_REDACTED_SPAN_ATTRIBUTE_NAMES = frozenset(
    {
        "exception.message",
        "exception.stacktrace",
        "status.description",
    }
)
_URL_ATTRIBUTE_NAMES = frozenset({"http.target", "http.url", "url.full", "url.path"})
_URL_HOST_ATTRIBUTE_NAMES = frozenset(
    {
        "http.host",
        "net.peer.name",
        "network.peer.address",
        "server.address",
        "url.domain",
    }
)
_AZURE_BLOB_HOST_SUFFIXES = (
    ".blob.core.windows.net",
    ".blob.core.usgovcloudapi.net",
    ".blob.core.chinacloudapi.cn",
)
_APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL = "APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL"


@dataclass(frozen=True, slots=True)
class AzureMonitorStatus:
    """Result of configuring the Azure Monitor hook."""

    enabled: bool
    reason: str


class SafeAzureMonitorSpanProcessor(SpanProcessor):
    """Sanitize OpenTelemetry spans before Azure Monitor export."""

    def on_start(self, span: Any, parent_context: Any | None = None) -> None:
        _sanitize_span(span)

    def _on_ending(self, span: Any) -> None:
        _sanitize_span(span)

    def on_end(self, span: Any) -> None:
        _sanitize_span(span)
        for event in getattr(span, "events", ()):
            _sanitize_attribute_owner(event)

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def configure_azure_monitor(settings: RuntimeSettings) -> AzureMonitorStatus:
    """Configure Azure Monitor when explicitly enabled and connection data exists."""

    global _azure_monitor_configured

    if not settings.azure_monitor_enabled:
        return AzureMonitorStatus(enabled=False, reason="disabled")

    if not settings.azure_monitor_connection_string:
        return AzureMonitorStatus(enabled=False, reason="missing_connection_string")

    if is_placeholder_azure_monitor_connection_string(settings.azure_monitor_connection_string):
        _logger.warning("Azure Monitor connection string is the local example placeholder.")
        return AzureMonitorStatus(enabled=False, reason="placeholder_connection_string")

    if _azure_monitor_configured:
        return AzureMonitorStatus(enabled=True, reason="already_configured")

    _set_default_otel_environment(settings)

    try:
        azure_monitor = importlib.import_module("azure.monitor.opentelemetry")
        configure = azure_monitor.configure_azure_monitor
        kwargs: dict[str, Any] = {
            "connection_string": settings.azure_monitor_connection_string,
            "disable_logging": False,
            "disable_tracing": False,
            "disable_offline_storage": not settings.azure_monitor_offline_storage_enabled,
            "enable_live_metrics": settings.azure_monitor_live_metrics_enabled,
            "disable_metrics": False,
            "enable_performance_counters": False,
            "sampling_ratio": 1.0,
            "browser_sdk_loader_config": {"enabled": False},
            "instrumentation_options": {"fastapi": {"enabled": False}},
            "span_processors": [SafeAzureMonitorSpanProcessor()],
            "log_record_processors": [SafeAzureMonitorLogRecordProcessor(settings)],
            "logging_formatter": AzureMonitorLogFormatter(),
        }
        if settings.azure_monitor_logger_name is not None:
            kwargs["logger_name"] = settings.azure_monitor_logger_name

        configure(**kwargs)
    except ImportError:
        _logger.warning("Azure Monitor OpenTelemetry package is not available.")
        return AzureMonitorStatus(enabled=False, reason="package_unavailable")
    except Exception as exc:
        _logger.warning(
            "Azure Monitor OpenTelemetry configuration failed.",
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={"exception_type": type(exc).__name__},
        )
        return AzureMonitorStatus(enabled=False, reason="configuration_failed")

    _azure_monitor_configured = True
    return AzureMonitorStatus(enabled=True, reason="configured")


def instrument_fastapi_app(
    app: FastAPI,
    status: AzureMonitorStatus,
    *,
    tracer_provider: object | None = None,
) -> bool:
    """Instrument the concrete FastAPI app after Azure Monitor is configured."""

    if not status.enabled:
        return False

    try:
        fastapi_instrumentation = importlib.import_module("opentelemetry.instrumentation.fastapi")
        instrumentor = fastapi_instrumentation.FastAPIInstrumentor()
        kwargs: dict[str, object] = {}
        if tracer_provider is not None:
            kwargs["tracer_provider"] = tracer_provider
        instrumentor.instrument_app(app, **kwargs)
    except Exception as exc:
        _logger.warning(
            "FastAPI Azure Monitor instrumentation failed.",
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={"exception_type": type(exc).__name__},
        )
        return False

    return True


def _set_default_otel_environment(settings: RuntimeSettings) -> None:
    environ.setdefault("OTEL_SERVICE_NAME", settings.service_name)
    environ["OTEL_METRICS_EXPORTER"] = "none"
    environ[_APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL] = "true"
    resource_attributes = _resource_attributes(settings)
    existing_resource_attributes = environ.get("OTEL_RESOURCE_ATTRIBUTES")

    if existing_resource_attributes:
        environ["OTEL_RESOURCE_ATTRIBUTES"] = (
            f"{existing_resource_attributes},{resource_attributes}"
        )
        return

    environ["OTEL_RESOURCE_ATTRIBUTES"] = resource_attributes


def _resource_attributes(settings: RuntimeSettings) -> str:
    return (
        f"service.name={settings.service_name},"
        f"deployment.environment.name={settings.environment},"
        f"deployment.environment={settings.environment}"
    )


def _sanitize_span(span: object) -> None:
    _sanitize_attribute_owner(span)

    status = getattr(span, "status", None)
    description = getattr(status, "description", None)
    if isinstance(description, str):
        safe_description = _safe_span_attribute_value("status.description", description)
        if (
            status is not None
            and isinstance(safe_description, str)
            and hasattr(status, "_description")
        ):
            status._description = safe_description


def _sanitize_attribute_owner(owner: object) -> None:
    attributes = _mutable_attributes(owner)
    if attributes is None:
        return

    safe_attributes = _safe_span_attributes(attributes)
    if getattr(attributes, "_immutable", False) and hasattr(owner, "_attributes"):
        cast(Any, owner)._attributes = safe_attributes
        return

    try:
        for key in tuple(attributes):
            if key not in safe_attributes:
                del attributes[key]
        for key, value in safe_attributes.items():
            attributes[key] = value
    except TypeError:
        if hasattr(owner, "_attributes"):
            cast(Any, owner)._attributes = safe_attributes


def _mutable_attributes(owner: object) -> MutableMapping[str, object] | None:
    attributes = getattr(owner, "attributes", None)
    if isinstance(attributes, MutableMapping):
        return cast(MutableMapping[str, object], attributes)

    backing_attributes = getattr(owner, "_attributes", None)
    if isinstance(backing_attributes, MutableMapping):
        return cast(MutableMapping[str, object], backing_attributes)

    return None


def _safe_span_attributes(
    attributes: MutableMapping[str, object],
) -> dict[str, object]:
    redact_url_path = _has_azure_blob_url_context(attributes)
    return {
        key: _safe_span_attribute_value(key, attributes[key], redact_url_path)
        for key in tuple(attributes)
        if key.lower() not in _REMOVED_SPAN_ATTRIBUTE_NAMES
    }


def _safe_span_attribute_value(
    key: str,
    value: object,
    redact_url_path: bool = False,
) -> object:
    normalized_key = key.lower()
    if normalized_key in _REDACTED_SPAN_ATTRIBUTE_NAMES:
        return REDACTED

    if normalized_key in _QUERY_STRING_ATTRIBUTE_NAMES and isinstance(value, str):
        value = _without_query_string(value)
        if redact_url_path and normalized_key in _URL_ATTRIBUTE_NAMES:
            value = _redact_url_path(value)

    return azure_monitor_attribute_value(key, value)


def _has_azure_blob_url_context(attributes: MutableMapping[str, object]) -> bool:
    for key, value in attributes.items():
        normalized_key = key.lower()
        if normalized_key in _URL_ATTRIBUTE_NAMES and isinstance(value, str):
            host = _host_from_url(value)
            if host is not None and _is_azure_blob_host(host):
                return True
        if normalized_key in _URL_HOST_ATTRIBUTE_NAMES and isinstance(value, str):
            if _is_azure_blob_host(value):
                return True

    return False


def _without_query_string(value: str) -> str:
    parts = urlsplit(value)
    if parts.query:
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment))

    path, separator, _query = value.partition("?")
    if separator:
        return path

    return value


def _redact_url_path(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        return urlunsplit((parts.scheme, parts.netloc, "/[redacted]", "", ""))

    if value.startswith("/"):
        return "/[redacted]"

    return value


def _host_from_url(value: str) -> str | None:
    parts = urlsplit(value)
    if not parts.netloc:
        return None

    return parts.hostname


def _is_azure_blob_host(value: str) -> bool:
    host = value.split(":", maxsplit=1)[0].strip().lower()
    return any(host.endswith(suffix) for suffix in _AZURE_BLOB_HOST_SUFFIXES)
