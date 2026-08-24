"""Expected failures raised by document review use cases."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from docmind_backend_runtime.errors import ConflictError, ValidationApplicationError


class DocumentReviewNotInitializedError(ConflictError):
    """Raised when no editable Review can be created for a document."""

    def __init__(self, *, document_id: UUID) -> None:
        super().__init__(
            code="DOCUMENT_REVIEW_NOT_INITIALIZED",
            message="Document Review is not available for editing yet.",
            details={"document_id": str(document_id)},
        )


class DocumentReviewVersionConflictError(ConflictError):
    """Raised when a save is based on an old Review version."""

    def __init__(self, *, details: Mapping[str, Any]) -> None:
        super().__init__(
            code="DOCUMENT_REVIEW_VERSION_CONFLICT",
            message="Document Review was changed by another user.",
            details=details,
        )


class DocumentReviewValidationError(ValidationApplicationError):
    """Raised when a submitted full snapshot is invalid."""

    def __init__(self, *, message: str, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(
            code="DOCUMENT_REVIEW_VALIDATION_ERROR",
            message=message,
            details=details,
        )


class DocumentApprovalDecisionRejectedError(ConflictError):
    """Raised when an actor cannot decide the active approval step."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details)


class DocumentApprovalSettingsConflictError(ConflictError):
    """Raised when global approval settings changed after they were loaded."""

    def __init__(self) -> None:
        super().__init__(
            code="DOCUMENT_APPROVAL_SETTINGS_CONFLICT",
            message="Document approval settings changed since they were loaded.",
        )
