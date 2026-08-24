"""Safe Azure Monitor log export helpers."""

from __future__ import annotations

import logging
from collections.abc import MutableMapping, Sequence
from typing import Any, cast

from docmind_backend_runtime.context import get_request_context
from docmind_backend_runtime.logging_sanitization import (
    REDACTED,
    sanitize_log_message,
    sanitize_log_value,
)
from docmind_backend_runtime.settings import RuntimeSettings

_REDACTED_AZURE_ATTRIBUTE_NAMES = frozenset(
    {
        "exception.message",
    }
)


class AzureMonitorLogFormatter(logging.Formatter):
    """Formatter used by the Azure Monitor OpenTelemetry logging handler."""

    def format(self, record: logging.LogRecord) -> str:
        return sanitize_log_message(record.getMessage())


class SafeAzureMonitorLogRecordProcessor:
    """Sanitize and enrich OpenTelemetry log records before Azure export."""

    def __init__(self, settings: RuntimeSettings) -> None:
        self._settings = settings

    def on_emit(self, log_record: Any) -> None:
        otel_record = getattr(log_record, "log_record", None)
        if otel_record is None:
            return

        body = getattr(otel_record, "body", None)
        if isinstance(body, str):
            otel_record.body = sanitize_log_message(body)

        attributes = getattr(otel_record, "attributes", None)
        if not isinstance(attributes, MutableMapping):
            return

        attribute_mapping = cast(MutableMapping[str, object], attributes)
        self._sanitize_attributes(attribute_mapping)
        self._add_runtime_context(attribute_mapping)

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    def _sanitize_attributes(self, attributes: MutableMapping[str, object]) -> None:
        for key in tuple(attributes):
            attributes[key] = azure_monitor_attribute_value(key, attributes[key])

    def _add_runtime_context(self, attributes: MutableMapping[str, object]) -> None:
        attributes["service_name"] = self._settings.service_name
        attributes["environment"] = self._settings.environment

        request_context = get_request_context()
        if request_context is None:
            return

        attributes["service_name"] = request_context.service_name
        attributes["environment"] = request_context.environment
        attributes["correlation_id"] = request_context.correlation_id


def azure_monitor_attribute_value(key: str, value: object) -> object:
    if key.lower() in _REDACTED_AZURE_ATTRIBUTE_NAMES:
        return REDACTED

    safe_value = sanitize_log_value(key, value)
    if isinstance(safe_value, str | int | float | bool):
        return safe_value
    if safe_value is None:
        return ""
    if isinstance(safe_value, Sequence) and not isinstance(
        safe_value,
        str | bytes | bytearray,
    ):
        sequence = cast(Sequence[object], safe_value)
        return [_azure_sequence_value(item) for item in sequence]

    return str(safe_value)


def _azure_sequence_value(value: object) -> str | int | float | bool:
    if isinstance(value, str | int | float | bool):
        return value

    return str(value)
