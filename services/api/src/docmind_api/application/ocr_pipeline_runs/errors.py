"""Application errors for OCR pipeline run workflows."""

from http import HTTPStatus
from uuid import UUID

from docmind_backend_runtime.errors import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    ValidationApplicationError,
)


class OcrPipelineRunNotFoundError(NotFoundError):
    """Raised when an OCR pipeline run id is not registered."""

    def __init__(self, *, run_id: UUID | str) -> None:
        super().__init__(
            code="OCR_PIPELINE_RUN_NOT_FOUND",
            message="OCR pipeline run not found.",
            details={"run_id": str(run_id)},
        )


class OcrPipelineRunDocumentNotFoundError(NotFoundError):
    """Raised when a run is requested for an unknown document."""

    def __init__(self, *, document_id: UUID | str) -> None:
        super().__init__(
            code="OCR_PIPELINE_RUN_DOCUMENT_NOT_FOUND",
            message="Document not found for OCR pipeline run.",
            details={"document_id": str(document_id)},
        )


class OcrPipelineRunNoPublishedPipelineError(ConflictError):
    """Raised when no runnable default published pipeline can be selected."""

    def __init__(self) -> None:
        super().__init__(
            code="OCR_PIPELINE_RUN_NO_PUBLISHED_DEFAULT",
            message="No published default OCR pipeline is available for direct runs.",
        )


class OcrPipelineRunAlreadyActiveError(ConflictError):
    """Raised when a document already has an active OCR pipeline run."""

    def __init__(self, *, document_id: UUID | str, run_id: UUID | str) -> None:
        super().__init__(
            code="OCR_PIPELINE_RUN_ALREADY_ACTIVE",
            message="An OCR pipeline run is already active for this document.",
            details={"document_id": str(document_id), "run_id": str(run_id)},
        )


class OcrPipelineRunPipelineNotRunnableError(ConflictError):
    """Raised when the selected published pipeline cannot be invoked safely."""

    def __init__(self, *, pipeline_id: UUID | str, reason: str) -> None:
        super().__init__(
            code="OCR_PIPELINE_RUN_PIPELINE_NOT_RUNNABLE",
            message="Published OCR pipeline cannot be used for a direct run.",
            details={"pipeline_id": str(pipeline_id), "reason": reason},
        )


class OcrPipelineRunUnknownDocumentSizeError(ConflictError):
    """Raised when a direct OCR run cannot prove the document size is safe."""

    def __init__(self, *, document_id: UUID | str) -> None:
        super().__init__(
            code="OCR_PIPELINE_RUN_DOCUMENT_SIZE_UNKNOWN",
            message="Document content size is unknown for direct OCR pipeline run.",
            details={"document_id": str(document_id)},
        )


class OcrPipelineRunLimitExceededError(ApplicationError):
    """Raised when a direct OCR run would exceed the guarded direct path limits."""

    def __init__(
        self,
        *,
        document_id: UUID | str,
        content_size_bytes: int,
        max_content_bytes: int,
    ) -> None:
        super().__init__(
            code="OCR_PIPELINE_RUN_LIMIT_EXCEEDED",
            message="Document exceeds the direct OCR pipeline run size limit.",
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            details={
                "document_id": str(document_id),
                "content_size_bytes": content_size_bytes,
                "max_content_bytes": max_content_bytes,
            },
        )


class OcrPipelineRunValidationError(ValidationApplicationError):
    """Raised when run input cannot be accepted."""

    def __init__(self, *, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(
            code="OCR_PIPELINE_RUN_VALIDATION_ERROR",
            message=message,
            details=details,
        )


class OcrPipelineRunLlmMagicUnavailableError(ApplicationError):
    """Raised when LLM Magic direct run invocation cannot be completed."""

    def __init__(self) -> None:
        super().__init__(
            code="OCR_PIPELINE_RUN_LLMMAGIC_UNAVAILABLE",
            message="LLM Magic OCR pipeline run service is unavailable.",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        )


class OcrPipelineRunInvocationIndeterminateError(RuntimeError):
    """Raised when a transport timeout cannot prove whether remote execution stopped."""
