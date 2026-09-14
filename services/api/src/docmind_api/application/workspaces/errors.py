"""Typed application failures for workspace registry operations."""

from docmind_backend_runtime.errors import BusinessRuleError, ConflictError, NotFoundError


class WorkspaceAdministrationUnavailableError(BusinessRuleError):
    """Raised when the active profile does not enable workspace administration."""

    def __init__(self) -> None:
        super().__init__(
            code="WORKSPACE_ADMINISTRATION_UNAVAILABLE",
            message="Workspace administration is not enabled by the active deployment profile.",
        )


class WorkspaceNotFoundError(NotFoundError):
    """Raised when no workspace has the supplied technical ID."""

    def __init__(self, *, workspace_id: object) -> None:
        super().__init__(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found.",
            details={"workspace_id": str(workspace_id)},
        )


class WorkspaceDirectoryConfigurationError(BusinessRuleError):
    """Raised when the configured directory dictionary is unavailable or inactive."""

    def __init__(self) -> None:
        super().__init__(
            code="WORKSPACE_DIRECTORY_NOT_AVAILABLE",
            message="The configured workspace directory is not available.",
        )


class WorkspaceDirectoryEntryConflictError(ConflictError):
    """Raised when a directory entry is already bound to a workspace."""

    def __init__(self, *, directory_entry_id: object) -> None:
        super().__init__(
            code="WORKSPACE_DIRECTORY_ENTRY_ALREADY_BOUND",
            message="Directory entry is already bound to a workspace.",
            details={"directory_entry_id": str(directory_entry_id)},
        )


class WorkspaceIdempotencyConflictError(ConflictError):
    """Raised when one idempotency key carries different registration input."""

    def __init__(self, *, idempotency_key: str) -> None:
        super().__init__(
            code="WORKSPACE_IDEMPOTENCY_CONFLICT",
            message="Idempotency key was already used with a different payload.",
            details={"idempotency_key": idempotency_key},
        )


class WorkspaceProvisioningNotRetryableError(BusinessRuleError):
    """Raised when retry is requested before a failed operation exists."""

    def __init__(self, *, workspace_id: object) -> None:
        super().__init__(
            code="WORKSPACE_PROVISIONING_NOT_RETRYABLE",
            message="Workspace provisioning can be retried only after a failed request.",
            details={"workspace_id": str(workspace_id)},
        )
