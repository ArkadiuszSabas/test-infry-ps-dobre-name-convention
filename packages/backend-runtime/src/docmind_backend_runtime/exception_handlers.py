"""Standard FastAPI exception handlers."""

import logging
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from pathlib import Path
from traceback import extract_tb
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.utils import is_body_allowed_for_status_code
from starlette.exceptions import HTTPException as StarletteHTTPException

from docmind_backend_runtime.context import get_correlation_id
from docmind_backend_runtime.errors import ApplicationError
from docmind_backend_runtime.settings import RuntimeSettings

ERROR_DETAILS: Mapping[str, Any] = {}
_RUNTIME_SETTINGS_STATE_KEY = "runtime_settings"
_logger = logging.getLogger("docmind_backend_runtime.exception_handlers")


def register_exception_handlers(app: FastAPI, *, settings: RuntimeSettings) -> None:
    """Register DocMind.ai standard exception handlers."""

    setattr(app.state, _RUNTIME_SETTINGS_STATE_KEY, settings)
    app.add_exception_handler(ApplicationError, handle_application_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)


async def handle_application_error(request: Request, exc: Exception) -> JSONResponse:
    """Convert known application errors to the standard envelope."""

    if not isinstance(exc, ApplicationError):
        raise exc

    if exc.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        _log_server_error(
            request=request,
            exc=exc,
            code=exc.code,
            message="Server application error.",
        )

    return _error_response(
        request=request,
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


async def handle_request_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """Convert FastAPI request validation errors to the standard envelope."""

    if not isinstance(exc, RequestValidationError):
        raise exc

    return _error_response(
        request=request,
        code="REQUEST_VALIDATION_ERROR",
        message="Request validation failed.",
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        details={"errors": _clean_validation_errors(exc.errors())},
    )


async def handle_http_exception(request: Request, exc: Exception) -> Response:
    """Convert Starlette HTTP exceptions to the standard envelope."""

    if not isinstance(exc, StarletteHTTPException):
        raise exc

    if exc.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        _log_server_error(
            request=request,
            exc=exc,
            code="HTTP_ERROR",
            message="Server HTTP error.",
        )

    if not is_body_allowed_for_status_code(exc.status_code):
        return _empty_response(
            request=request,
            status_code=exc.status_code,
            headers=exc.headers,
        )

    return _error_response(
        request=request,
        code="HTTP_ERROR",
        message=_http_exception_message(exc),
        status_code=exc.status_code,
        details=ERROR_DETAILS,
        headers=exc.headers,
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Hide unexpected exception details from API responses."""

    _log_server_error(
        request=request,
        exc=exc,
        code="INTERNAL_SERVER_ERROR",
        message="Unhandled request error.",
    )
    return _error_response(
        request=request,
        code="INTERNAL_SERVER_ERROR",
        message="Internal server error.",
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        details=ERROR_DETAILS,
    )


def _error_response(
    *,
    request: Request,
    code: str,
    message: str,
    status_code: int,
    details: Mapping[str, Any],
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    settings = _runtime_settings(request)
    response = JSONResponse(
        status_code=status_code,
        headers=dict(headers or {}),
        content={
            "error": {
                "code": code,
                "message": message,
                "details": dict(details),
            },
        },
    )
    correlation_id = _correlation_id_from_request(request)

    if correlation_id is not None:
        response.headers[settings.correlation_header_name] = correlation_id

    return response


def _empty_response(
    *,
    request: Request,
    status_code: int,
    headers: Mapping[str, str] | None = None,
) -> Response:
    settings = _runtime_settings(request)
    response = Response(status_code=status_code, headers=dict(headers or {}))
    correlation_id = _correlation_id_from_request(request)

    if correlation_id is not None:
        response.headers[settings.correlation_header_name] = correlation_id

    return response


def _runtime_settings(request: Request) -> RuntimeSettings:
    settings: object = getattr(request.app.state, _RUNTIME_SETTINGS_STATE_KEY)
    if isinstance(settings, RuntimeSettings):
        return settings

    raise RuntimeError("Runtime settings are not registered on the FastAPI app.")


def _correlation_id_from_request(request: Request) -> str | None:
    context_correlation_id = get_correlation_id()
    if context_correlation_id is not None:
        return context_correlation_id

    state_correlation_id: object = getattr(request.state, "correlation_id", None)
    if isinstance(state_correlation_id, str):
        return state_correlation_id

    return None


def _safe_stack_trace(exc: Exception) -> list[dict[str, object]]:
    return [
        {
            "file": Path(frame.filename).name,
            "line": frame.lineno,
            "function": frame.name,
        }
        for frame in extract_tb(exc.__traceback__)
    ]


def _log_server_error(
    *,
    request: Request,
    exc: Exception,
    code: str,
    message: str,
) -> None:
    _logger.error(
        message,
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={
            "correlation_id": _correlation_id_from_request(request),
            "error_code": code,
            "exception_type": type(exc).__name__,
            "stack_trace_frames": _safe_stack_trace(exc),
        },
    )


def _clean_validation_errors(errors: Sequence[Any]) -> list[dict[str, Any]]:
    cleaned_errors: list[dict[str, Any]] = []

    for error in errors:
        if not isinstance(error, Mapping):
            continue
        error_mapping = cast(Mapping[str, Any], error)

        cleaned_errors.append(
            {
                "loc": error_mapping.get("loc", ()),
                "msg": error_mapping.get("msg", "Invalid input."),
                "type": error_mapping.get("type", "value_error"),
            },
        )

    return cleaned_errors


def _http_exception_message(exc: StarletteHTTPException) -> str:
    detail = _http_exception_detail(exc)
    if isinstance(detail, str):
        return detail

    try:
        return HTTPStatus(exc.status_code).phrase
    except ValueError:
        return "HTTP error."


def _http_exception_detail(exc: StarletteHTTPException) -> object:
    return getattr(exc, "detail", None)
