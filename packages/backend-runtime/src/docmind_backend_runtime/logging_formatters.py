"""Runtime log formatters for console, stdout, and Seq sinks."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from traceback import FrameSummary, extract_tb
from types import TracebackType
from typing import cast

from docmind_backend_runtime.context import get_request_context
from docmind_backend_runtime.logging_sanitization import (
    sanitize_log_message,
    sanitize_log_value,
)
from docmind_backend_runtime.settings import RuntimeSettings

_LOG_RECORD_RESERVED_ATTRIBUTES = frozenset(
    logging.LogRecord(
        name="reserved",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="reserved",
        args=(),
        exc_info=None,
    ).__dict__,
) | {"asctime", "message"}
_LEVEL_COLORS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[35m",
}
_RESET_COLOR = "\033[0m"
_PRETTY_TRACEBACK_MAX_FRAMES = 10
_FRAMEWORK_TRACEBACK_PATH_MARKERS = (
    "/site-packages/anyio/",
    "/site-packages/fastapi/",
    "/site-packages/starlette/",
    "/site-packages/uvicorn/",
    "/asyncio/",
)


class PrettyConsoleFormatter(logging.Formatter):
    """Human-readable, colored formatter for local terminals."""

    def __init__(self, settings: RuntimeSettings) -> None:
        super().__init__()
        self._settings = settings

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).astimezone().strftime("%H:%M:%S")
        level = self._format_level(record.levelname)
        properties = log_properties(record, self._settings, include_service=False)
        context = self._format_context(properties)
        message = sanitize_log_message(record.getMessage())
        exception = _format_pretty_exception(record, properties)

        return f"{timestamp} {level} {context}{message}{exception}".rstrip()

    def _format_level(self, level_name: str) -> str:
        label = f"{level_name:<8}"
        if not self._settings.console_color_enabled:
            return label

        color = _LEVEL_COLORS.get(level_name)
        if color is None:
            return label

        return f"{color}{label}{_RESET_COLOR}"

    @staticmethod
    def _format_context(properties: Mapping[str, object]) -> str:
        parts: list[str] = []
        correlation_id = properties.get("correlation_id")
        if isinstance(correlation_id, str):
            parts.append(f"corr={correlation_id}")

        method = properties.get("http_method")
        path = properties.get("http_path")
        status_code = properties.get("http_status_code")
        duration_ms = properties.get("duration_ms")
        if isinstance(method, str) and isinstance(path, str):
            request = f"{method} {path}"
            if isinstance(status_code, int):
                request = f"{request} {status_code}"
            if isinstance(duration_ms, int | float):
                request = f"{request} {duration_ms:.1f}ms"
            parts.append(request)

        if not parts:
            return ""

        return f"[{' | '.join(parts)}] "


class JsonLogFormatter(logging.Formatter):
    """JSON formatter for stdout/container logs."""

    def __init__(self, settings: RuntimeSettings) -> None:
        super().__init__()
        self._settings = settings

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": _utc_timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_log_message(record.getMessage()),
        }
        payload.update(log_properties(record, self._settings, include_service=True))
        exception_type = _exception_type(record.exc_info)
        if exception_type is not None:
            payload["exception_type"] = exception_type
        exception_traceback = _exception_traceback(record.exc_info)
        if exception_traceback is not None:
            payload["stack_trace"] = exception_traceback

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class SeqCompactLogFormatter(logging.Formatter):
    """Seq Compact Log Event Format formatter."""

    def __init__(self, settings: RuntimeSettings) -> None:
        super().__init__()
        self._settings = settings

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "@t": _utc_timestamp(record),
            "@mt": sanitize_log_message(record.getMessage()),
            "@l": record.levelname,
            "logger": record.name,
        }
        payload.update(log_properties(record, self._settings, include_service=True))
        exception_traceback = _exception_traceback(record.exc_info)
        if exception_traceback is not None:
            payload["@x"] = exception_traceback

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def log_properties(
    record: logging.LogRecord,
    settings: RuntimeSettings,
    *,
    include_service: bool,
) -> dict[str, object]:
    """Return safe structured properties for a log record."""

    properties: dict[str, object] = {}
    if include_service:
        properties["service_name"] = settings.service_name
    properties["environment"] = settings.environment

    for key, value in record.__dict__.items():
        if key in _LOG_RECORD_RESERVED_ATTRIBUTES:
            continue
        properties[key] = sanitize_log_value(key, value)

    request_context = get_request_context()
    if request_context is not None:
        if include_service:
            properties["service_name"] = request_context.service_name
        properties["environment"] = request_context.environment
        properties["correlation_id"] = request_context.correlation_id

    return properties


def _utc_timestamp(record: logging.LogRecord) -> str:
    timestamp = datetime.fromtimestamp(record.created, tz=UTC)
    return timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _exception_type(exc_info: object) -> str | None:
    typed_exc_info = _typed_exception_info(exc_info)
    if typed_exc_info is None:
        return None

    return typed_exc_info[0].__name__


def _exception_traceback(exc_info: object) -> str | None:
    typed_exc_info = _typed_exception_info(exc_info)
    if typed_exc_info is None:
        return None

    formatted = logging.Formatter().formatException(typed_exc_info)
    return sanitize_log_message(formatted)


def _format_pretty_exception(
    record: logging.LogRecord,
    properties: Mapping[str, object],
) -> str:
    typed_exc_info = _typed_exception_info(record.exc_info)
    if typed_exc_info is not None:
        exception_class, exception, _traceback = typed_exc_info
        exception_message = sanitize_log_message(str(exception).strip())
        headline = f" {exception_class.__name__}"
        if exception_message:
            headline = f"{headline}: {exception_message}"

        frames = _pretty_traceback_frames(typed_exc_info)
        if not frames:
            return headline

        formatted_frames = [_format_pretty_frame(frame) for frame in frames]
        headline = f"{headline} at {formatted_frames[-1]}"
        stack = "\n".join(f"  at {frame}" for frame in formatted_frames)
        return f"{headline}\n{stack}"

    parts: list[str] = []
    exception_type = _exception_type(record.exc_info)
    if exception_type is None:
        extra_exception_type = properties.get("exception_type")
        if isinstance(extra_exception_type, str):
            exception_type = extra_exception_type
    if exception_type is not None:
        parts.append(f"exception={exception_type}")

    top_frame = _top_stack_frame(properties.get("stack_trace"))
    if top_frame is not None:
        parts.append(f"at={top_frame}")

    if not parts:
        return ""

    return f" {' '.join(parts)}"


def _typed_exception_info(
    exc_info: object,
) -> tuple[type[BaseException], BaseException, TracebackType | None] | None:
    if not isinstance(exc_info, tuple):
        return None

    values = cast(tuple[object, ...], exc_info)
    if len(values) != 3:
        return None

    exception_class, exception, traceback = values
    if not isinstance(exception_class, type) or not issubclass(exception_class, BaseException):
        return None
    if not isinstance(exception, BaseException):
        return None
    if traceback is not None and not isinstance(traceback, TracebackType):
        return None

    return exception_class, exception, traceback


def _pretty_traceback_frames(
    exc_info: tuple[type[BaseException], BaseException, TracebackType | None],
) -> list[FrameSummary]:
    traceback = exc_info[2]
    if traceback is None:
        return []

    frames = list(extract_tb(traceback))
    relevant_frames = [frame for frame in frames if not _is_framework_frame(frame)]
    return relevant_frames[-_PRETTY_TRACEBACK_MAX_FRAMES:]


def _is_framework_frame(frame: FrameSummary) -> bool:
    normalized_path = f"/{frame.filename.replace('\\', '/').lower().lstrip('/')}"
    return any(marker in normalized_path for marker in _FRAMEWORK_TRACEBACK_PATH_MARKERS)


def _format_pretty_frame(frame: FrameSummary) -> str:
    file_name = frame.filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    return f"{file_name}:{frame.lineno} in {frame.name}"


def _top_stack_frame(stack_trace: object) -> str | None:
    if not isinstance(stack_trace, Sequence) or isinstance(
        stack_trace,
        str | bytes | bytearray,
    ):
        return None
    stack_frames = cast(Sequence[object], stack_trace)
    if not stack_frames:
        return None

    frame = stack_frames[-1]
    if not isinstance(frame, Mapping):
        return None

    frame_mapping = cast(Mapping[str, object], frame)
    file_name = frame_mapping.get("file")
    line = frame_mapping.get("line")
    function = frame_mapping.get("function")
    if not isinstance(file_name, str):
        return None
    if not isinstance(line, int):
        return None
    if not isinstance(function, str):
        return None

    return f"{file_name}:{line}:{function}"
