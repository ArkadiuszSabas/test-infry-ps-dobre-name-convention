"""Structured logging configuration for backend services."""

from __future__ import annotations

import logging
import sys
from typing import TextIO

from docmind_backend_runtime.logging_formatters import (
    JsonLogFormatter,
    PrettyConsoleFormatter,
    SeqCompactLogFormatter,
)
from docmind_backend_runtime.logging_sanitization import sanitize_log_value
from docmind_backend_runtime.seq_logging import SeqLogHandler
from docmind_backend_runtime.settings import RuntimeSettings

__all__ = [
    "JsonLogFormatter",
    "PrettyConsoleFormatter",
    "SeqCompactLogFormatter",
    "configure_logging",
    "sanitize_log_value",
]

_DOCMIND_HANDLER_MARKER = "_docmind_handler"
_DOCMIND_FILTER_MARKER = "_docmind_filter"
_HANDLED_ASGI_EXCEPTION_MESSAGE = "Exception in ASGI application"


class _HandledAsgiExceptionFilter(logging.Filter):
    """Suppress Uvicorn's duplicate for exceptions logged by the runtime handler."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not (
            record.exc_info is not None
            and record.getMessage().strip() == _HANDLED_ASGI_EXCEPTION_MESSAGE
        )


def configure_logging(settings: RuntimeSettings, *, stream: TextIO | None = None) -> None:
    """Configure root logging handlers for the selected runtime sinks."""

    root_logger = logging.getLogger()
    root_logger.setLevel(_parse_log_level(settings.log_level))
    _remove_docmind_handlers(root_logger)
    _set_default_library_log_levels()

    if settings.console_logs_enabled:
        console_handler = logging.StreamHandler(_console_stream(settings, stream))
        _mark_docmind_handler(console_handler)
        console_handler.setLevel(_parse_log_level(settings.log_level))
        if settings.console_log_format == "json":
            console_handler.setFormatter(JsonLogFormatter(settings))
        else:
            console_handler.setFormatter(PrettyConsoleFormatter(settings))
        root_logger.addHandler(console_handler)

    if settings.seq_enabled and settings.environment == "local":
        seq_handler = SeqLogHandler(settings)
        _mark_docmind_handler(seq_handler)
        seq_handler.setLevel(_parse_log_level(settings.log_level))
        seq_handler.setFormatter(SeqCompactLogFormatter(settings))
        root_logger.addHandler(seq_handler)

    _configure_framework_loggers(settings)


def _parse_log_level(level_name: str) -> int:
    level = logging.getLevelNamesMapping().get(level_name.upper())
    if isinstance(level, int):
        return level

    return logging.INFO


def _set_default_library_log_levels() -> None:
    for logger_name in ("azure", "httpx", "opentelemetry", "urllib3"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def _configure_framework_loggers(settings: RuntimeSettings) -> None:
    log_level = _parse_log_level(settings.log_level)
    for logger_name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        _remove_docmind_filters(logger)
        logger.disabled = False
        logger.propagate = True
        logger.setLevel(log_level)

    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    asgi_exception_filter = _HandledAsgiExceptionFilter()
    _mark_docmind_filter(asgi_exception_filter)
    uvicorn_error_logger.addFilter(asgi_exception_filter)

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.disabled = True


def _console_stream(settings: RuntimeSettings, stream: TextIO | None) -> TextIO:
    if stream is not None:
        return stream
    if settings.console_log_format == "json":
        return sys.stdout

    return sys.stderr


def _remove_docmind_handlers(logger: logging.Logger) -> None:
    for handler in tuple(logger.handlers):
        if getattr(handler, _DOCMIND_HANDLER_MARKER, False):
            logger.removeHandler(handler)
            handler.close()


def _mark_docmind_handler(handler: logging.Handler) -> None:
    setattr(handler, _DOCMIND_HANDLER_MARKER, True)


def _remove_docmind_filters(logger: logging.Logger) -> None:
    for log_filter in tuple(logger.filters):
        if getattr(log_filter, _DOCMIND_FILTER_MARKER, False):
            logger.removeFilter(log_filter)


def _mark_docmind_filter(log_filter: logging.Filter) -> None:
    setattr(log_filter, _DOCMIND_FILTER_MARKER, True)
