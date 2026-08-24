"""Shared observability setup for backend services."""

from dataclasses import dataclass

from docmind_backend_runtime.logging_config import configure_logging
from docmind_backend_runtime.settings import RuntimeSettings
from docmind_backend_runtime.telemetry import AzureMonitorStatus, configure_azure_monitor


@dataclass(frozen=True, slots=True)
class ObservabilityStatus:
    """Result of configuring runtime observability."""

    azure_monitor: AzureMonitorStatus


def configure_observability(settings: RuntimeSettings) -> ObservabilityStatus:
    """Configure logging and optional telemetry for a service runtime."""

    configure_logging(settings)
    azure_monitor_status = configure_azure_monitor(settings)
    return ObservabilityStatus(azure_monitor=azure_monitor_status)
