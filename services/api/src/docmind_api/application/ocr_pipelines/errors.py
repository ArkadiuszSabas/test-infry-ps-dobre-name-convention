"""Application errors for OCR pipeline configuration workflows."""

from collections.abc import Sequence
from http import HTTPStatus
from typing import Any
from uuid import UUID

from docmind_api.domain.ocr_pipelines.models import OcrPipelineDiagnostic
from docmind_backend_runtime.errors import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    ValidationApplicationError,
)


class OcrPipelineAlreadyExistsError(ConflictError):
    """Raised when a pipeline name is already registered."""

    def __init__(self, *, name: str) -> None:
        super().__init__(
            code="OCR_PIPELINE_ALREADY_EXISTS",
            message="OCR pipeline already exists.",
            details={"name": name},
        )
        self.name = name


class OcrPipelineNotFoundError(NotFoundError):
    """Raised when a pipeline id is not registered."""

    def __init__(self, *, pipeline_id: UUID | str) -> None:
        pipeline_id_value = str(pipeline_id)
        super().__init__(
            code="OCR_PIPELINE_NOT_FOUND",
            message="OCR pipeline not found.",
            details={"pipeline_id": pipeline_id_value},
        )
        self.pipeline_id = pipeline_id_value


class OcrPipelineValidationError(ValidationApplicationError):
    """Raised when pipeline command input is invalid."""

    def __init__(
        self,
        *,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="OCR_PIPELINE_VALIDATION_ERROR",
            message=message,
            details=details,
        )


class OcrPipelineLifecycleError(ConflictError):
    """Raised when an operation is invalid for the current pipeline lifecycle."""

    def __init__(
        self,
        *,
        pipeline_id: UUID | str,
        message: str,
    ) -> None:
        super().__init__(
            code="OCR_PIPELINE_LIFECYCLE_CONFLICT",
            message=message,
            details={"pipeline_id": str(pipeline_id)},
        )


class OcrConfidenceColorSettingsConflictError(ConflictError):
    """Raised when confidence colors changed after an administrator loaded them."""

    def __init__(self) -> None:
        super().__init__(
            code="OCR_CONFIDENCE_COLOR_SETTINGS_CONFLICT",
            message="OCR confidence color settings changed since they were loaded.",
        )


class OcrPipelineLlmMagicUnavailableError(ApplicationError):
    """Raised when LLM Magic cannot serve OCR pipeline configuration data."""

    def __init__(self, *, operation: str) -> None:
        super().__init__(
            code="OCR_PIPELINE_LLMMAGIC_UNAVAILABLE",
            message="LLM Magic OCR pipeline configuration service is unavailable.",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            details={"operation": operation},
        )


class OcrPipelineValidationFailedError(ValidationApplicationError):
    """Raised when a publish operation is blocked by validation diagnostics."""

    def __init__(
        self,
        *,
        pipeline_id: UUID | str,
        diagnostics: Sequence[OcrPipelineDiagnostic],
    ) -> None:
        super().__init__(
            code="OCR_PIPELINE_VALIDATION_FAILED",
            message="OCR pipeline validation failed.",
            details={
                "pipeline_id": str(pipeline_id),
                "diagnostics": tuple(diagnostic.as_details() for diagnostic in diagnostics),
            },
        )
