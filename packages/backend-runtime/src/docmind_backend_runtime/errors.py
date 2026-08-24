"""Framework-free application error types."""

from collections.abc import Mapping
from http import HTTPStatus
from types import MappingProxyType
from typing import Any


class ApplicationError(Exception):
    """Base class for expected application failures."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = MappingProxyType(dict(details or {}))


class NotFoundError(ApplicationError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        *,
        message: str = "Resource not found.",
        code: str = "NOT_FOUND",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=HTTPStatus.NOT_FOUND,
            details=details,
        )


class ValidationApplicationError(ApplicationError):
    """Raised when a use case rejects invalid input."""

    def __init__(
        self,
        *,
        message: str = "Validation failed.",
        code: str = "VALIDATION_ERROR",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details,
        )


class BusinessRuleError(ApplicationError):
    """Raised when a business rule prevents an operation."""

    def __init__(
        self,
        *,
        message: str = "Business rule violation.",
        code: str = "BUSINESS_RULE_VIOLATION",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details,
        )


class ConflictError(ApplicationError):
    """Raised when the requested operation conflicts with current state."""

    def __init__(
        self,
        *,
        message: str = "Resource conflict.",
        code: str = "CONFLICT",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=HTTPStatus.CONFLICT,
            details=details,
        )
