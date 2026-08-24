"""Internal OCR endpoint access guard wiring."""

from collections.abc import Callable
from http import HTTPStatus

from docmind_backend_runtime import (
    ApplicationError,
    RuntimeSettings,
)

_ALLOWED_INTERNAL_OCR_ENVIRONMENTS = frozenset({"dev", "local", "sb1", "sb2", "sb3", "test"})


def internal_ocr_access_is_allowed(runtime_settings: RuntimeSettings) -> bool:
    """Return whether stage-1 internal-only OCR routes may run."""

    return runtime_settings.environment.lower() in _ALLOWED_INTERNAL_OCR_ENVIRONMENTS


def get_internal_ocr_access_dependency(
    runtime_settings: RuntimeSettings,
) -> Callable[[], None]:
    """Return the temporary internal OCR access guard for the current runtime."""

    if internal_ocr_access_is_allowed(runtime_settings):
        return _allow_internal_ocr_access

    return _deny_internal_ocr_access


def _allow_internal_ocr_access() -> None:
    return None


def _deny_internal_ocr_access() -> None:
    raise ApplicationError(
        code="INTERNAL_ENDPOINT_AUTH_NOT_CONFIGURED",
        message="Internal endpoint authentication is not configured.",
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
    )
