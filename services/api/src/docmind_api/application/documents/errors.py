"""Application errors for the document registry."""

from collections.abc import Mapping
from http import HTTPStatus

from docmind_backend_runtime.errors import (
    ApplicationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationApplicationError,
)


class DocumentAlreadyExistsError(ConflictError):
    """Raised when the generated document id already exists."""

    def __init__(self, *, document_id: str) -> None:
        super().__init__(
            code="DOCUMENT_ALREADY_EXISTS",
            message="Document already exists.",
            details={"document_id": document_id},
        )
        self.document_id = document_id


class DocumentIngestValidationError(ValidationApplicationError):
    """Raised when document ingest input is invalid."""

    def __init__(
        self,
        *,
        message: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(
            code="DOCUMENT_INGEST_VALIDATION_ERROR",
            message=message,
            details=details,
        )


class DocumentContentTooLargeError(ApplicationError):
    """Raised when document content exceeds the configured document size limit."""

    def __init__(self, *, max_content_bytes: int) -> None:
        super().__init__(
            code="DOCUMENT_CONTENT_TOO_LARGE",
            message="Document content exceeds the configured maximum size.",
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            details={"max_content_bytes": max_content_bytes},
        )


class DocumentListValidationError(ValidationApplicationError):
    """Raised when document list input is invalid."""

    def __init__(
        self,
        *,
        message: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(
            code="DOCUMENT_LIST_VALIDATION_ERROR",
            message=message,
            details=details,
        )


class DocumentNotFoundError(NotFoundError):
    """Raised when a document registry entry cannot be found."""

    def __init__(self, *, document_id: object) -> None:
        super().__init__(
            code="DOCUMENT_NOT_FOUND",
            message="Document not found.",
            details={"document_id": str(document_id)},
        )


class DocumentDeleteForbiddenError(ApplicationError):
    """Raised when an actor lacks the dedicated permanent-delete permission."""

    def __init__(self) -> None:
        super().__init__(
            code="DOCUMENT_DELETE_FORBIDDEN",
            message="Permanent document deletion is not allowed.",
            status_code=HTTPStatus.FORBIDDEN,
        )


class DocumentDeleteConnectorHandlerRequiredError(ConflictError):
    """Raised when connector provenance cannot be handled by the active profile."""

    def __init__(self) -> None:
        super().__init__(
            code="DOCUMENT_DELETE_CONNECTOR_HANDLER_REQUIRED",
            message="The active connector profile cannot safely prepare this deletion.",
        )


class DocumentDeleteBlockedError(ConflictError):
    """Raised when a connector policy blocks local purge."""

    def __init__(self) -> None:
        super().__init__(
            code="DOCUMENT_DELETE_BLOCKED",
            message="Permanent deletion is blocked by the document connector.",
        )


class DocumentDeleteRetryableError(ApplicationError):
    """Raised after a retryable connector, storage, or database failure."""

    def __init__(self) -> None:
        super().__init__(
            code="DOCUMENT_DELETE_RETRYABLE",
            message="Permanent deletion did not finish and can be retried.",
            status_code=HTTPStatus.BAD_GATEWAY,
        )


class DocumentDeleteAmbiguousError(ApplicationError):
    """Raised when connector cleanup cannot yet be reconciled safely."""

    def __init__(self) -> None:
        super().__init__(
            code="DOCUMENT_DELETE_AMBIGUOUS",
            message="Permanent deletion has an ambiguous connector result.",
            status_code=HTTPStatus.BAD_GATEWAY,
        )


class DocumentArchivedError(ConflictError):
    """Raised when a mutation targets an approved, immutable document."""

    def __init__(self, *, document_id: object) -> None:
        super().__init__(
            code="DOCUMENT_ARCHIVED_IMMUTABLE",
            message="Approved documents are archived and cannot be modified.",
            details={"document_id": str(document_id)},
        )


class DocumentContentNotFoundError(NotFoundError):
    """Raised when the registry entry points to missing stored content."""

    def __init__(self, *, document_id: object) -> None:
        super().__init__(
            code="DOCUMENT_CONTENT_NOT_FOUND",
            message="Document content was not found in storage.",
            details={"document_id": str(document_id)},
        )


class DocumentMetadataValidationError(ValidationApplicationError):
    """Raised when submitted document metadata does not match the inherited schema."""

    def __init__(self, *, details: Mapping[str, object]) -> None:
        super().__init__(
            code="DOCUMENT_METADATA_VALIDATION_ERROR",
            message="Document metadata does not match the selected document type schema.",
            details=details,
        )


class DocumentMetadataSchemaConfigurationError(ApplicationError):
    """Raised when inherited document metadata schema configuration is inconsistent."""

    def __init__(
        self,
        *,
        missing_attribute_ids: tuple[str, ...] = (),
        invalid_dictionary_attribute_ids: tuple[str, ...] = (),
    ) -> None:
        details: dict[str, tuple[str, ...]] = {
            "missing_attribute_ids": missing_attribute_ids,
        }
        if invalid_dictionary_attribute_ids:
            details["invalid_dictionary_attribute_ids"] = invalid_dictionary_attribute_ids
        super().__init__(
            code="DOCUMENT_METADATA_SCHEMA_CONFIGURATION_ERROR",
            message="Document metadata schema configuration is inconsistent.",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details,
        )


class DocumentTypeInactiveError(BusinessRuleError):
    """Raised when ingest references an inactive document type."""

    def __init__(self, *, document_type_id: object) -> None:
        document_type_id_value = str(document_type_id)
        super().__init__(
            code="DOCUMENT_TYPE_INACTIVE",
            message="Document type is inactive and cannot accept new documents.",
            details={"document_type_id": document_type_id_value},
        )
        self.document_type_id = document_type_id_value


class DocumentTypeChangeConfirmationRequiredError(ConflictError):
    """Raised when a reviewer must acknowledge a material type-change impact."""

    def __init__(self, *, impact: Mapping[str, object]) -> None:
        super().__init__(
            code="DOCUMENT_TYPE_CHANGE_CONFIRMATION_REQUIRED",
            message="Changing the document type affects its metadata validation.",
            details={"impact": dict(impact)},
        )


class DocumentTypeUnchangedError(ConflictError):
    """Raised when a reviewer selects the document's current type."""

    def __init__(self, *, document_id: object, document_type_id: object) -> None:
        super().__init__(
            code="DOCUMENT_TYPE_UNCHANGED",
            message="Document already has the selected document type.",
            details={"document_id": str(document_id), "document_type_id": str(document_type_id)},
        )


class DocumentStorageWriteError(ApplicationError):
    """Raised when raw content storage fails during ingest."""

    def __init__(self) -> None:
        super().__init__(
            code="DOCUMENT_STORAGE_WRITE_FAILED",
            message="Document content could not be stored.",
            status_code=HTTPStatus.BAD_GATEWAY,
        )


class DocumentStorageReadError(ApplicationError):
    """Raised when raw content storage cannot be read for preview."""

    def __init__(self, *, document_id: object) -> None:
        super().__init__(
            code="DOCUMENT_STORAGE_READ_FAILED",
            message="Document content could not be read from storage.",
            status_code=HTTPStatus.BAD_GATEWAY,
            details={"document_id": str(document_id)},
        )


class DocumentPreviewUnsupportedError(ApplicationError):
    """Raised when stored document content cannot be rendered as PDF."""

    def __init__(self, *, document_id: object) -> None:
        super().__init__(
            code="DOCUMENT_PREVIEW_UNSUPPORTED",
            message="Document preview supports only stored PDF content.",
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            details={
                "document_id": str(document_id),
                "supported_content_type": "application/pdf",
            },
        )
