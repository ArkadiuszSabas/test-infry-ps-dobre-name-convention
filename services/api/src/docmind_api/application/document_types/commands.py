"""Document type catalog command and error types."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from docmind_api.application.document_types.ports import DocumentTypeExtensionValuePayload
from docmind_api.domain.document_types.models import DocumentType, DocumentTypeUsage
from docmind_backend_runtime.errors import (
    ConflictError,
    NotFoundError,
    ValidationApplicationError,
)


@dataclass(frozen=True, slots=True)
class CreateDocumentTypeCommand:
    """Input for creating a document type catalog entry."""

    name: str
    external_id: str | None = None
    description: str | None = None
    id: str | None = None
    extension_values: tuple[DocumentTypeExtensionValuePayload, ...] = ()


class PreserveDocumentTypeDescription:
    """Marker for update commands that keep the stored description unchanged."""

    __slots__ = ()


PRESERVE_DOCUMENT_TYPE_DESCRIPTION = PreserveDocumentTypeDescription()
type DocumentTypeDescriptionUpdate = str | None | PreserveDocumentTypeDescription


class PreserveDocumentTypeExternalId:
    """Marker for update commands that keep the stored external ID unchanged."""

    __slots__ = ()


PRESERVE_DOCUMENT_TYPE_EXTERNAL_ID = PreserveDocumentTypeExternalId()
type DocumentTypeExternalIdUpdate = str | None | PreserveDocumentTypeExternalId


class PreserveDocumentTypeExtensionValues:
    """Marker for update commands that keep dynamic extension values unchanged."""

    __slots__ = ()


PRESERVE_DOCUMENT_TYPE_EXTENSION_VALUES = PreserveDocumentTypeExtensionValues()
type DocumentTypeExtensionValuesUpdate = (
    tuple[DocumentTypeExtensionValuePayload, ...] | PreserveDocumentTypeExtensionValues
)


@dataclass(frozen=True, slots=True)
class UpdateDocumentTypeCommand:
    """Input for editing business fields of an existing document type."""

    document_type_id: UUID | str
    name: str
    external_id: DocumentTypeExternalIdUpdate = PRESERVE_DOCUMENT_TYPE_EXTERNAL_ID
    description: DocumentTypeDescriptionUpdate = PRESERVE_DOCUMENT_TYPE_DESCRIPTION
    extension_values: DocumentTypeExtensionValuesUpdate = PRESERVE_DOCUMENT_TYPE_EXTENSION_VALUES


@dataclass(frozen=True, slots=True)
class DeactivateDocumentTypeCommand:
    """Input for deactivating an existing document type."""

    document_type_id: UUID | str


@dataclass(frozen=True, slots=True)
class DeleteDocumentTypeCommand:
    """Input for permanently deleting an unused document type."""

    document_type_id: UUID | str


@dataclass(frozen=True, slots=True)
class DeleteDocumentTypeResult:
    """Result of permanently deleting a document type."""

    document_type_id: UUID
    deleted: bool


class DocumentTypeListStatus(StrEnum):
    """Status filter for document type catalog listing."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class DocumentTypeListResult:
    """Result of listing document types with status counters."""

    document_types: tuple[DocumentType, ...]
    total_count: int
    active_count: int
    inactive_count: int
    status: DocumentTypeListStatus

    @property
    def returned_count(self) -> int:
        """Return the number of document types returned by the selected filter."""

        return len(self.document_types)


class DocumentTypeAlreadyExistsError(ConflictError):
    """Raised when a document type external_id is already registered."""

    def __init__(
        self,
        *,
        external_id: str | None = None,
        document_type_id: str | None = None,
    ) -> None:
        external_id_value = external_id or document_type_id or ""
        super().__init__(
            code="DOCUMENT_TYPE_ALREADY_EXISTS",
            message="Document type already exists.",
            details={"external_id": external_id_value},
        )
        self.external_id = external_id_value


class DocumentTypeNotFoundError(NotFoundError):
    """Raised when a document type id does not exist."""

    def __init__(self, *, document_type_id: object) -> None:
        document_type_id_value = str(document_type_id)
        super().__init__(
            code="DOCUMENT_TYPE_NOT_FOUND",
            message="Document type not found.",
            details={"document_type_id": document_type_id_value},
        )
        self.document_type_id = document_type_id_value


class DocumentTypeInUseError(ConflictError):
    """Raised when blocking dependencies prevent permanent deletion."""

    def __init__(self, *, document_type_id: object, usage: DocumentTypeUsage) -> None:
        document_type_id_value = str(document_type_id)
        super().__init__(
            code="DOCUMENT_TYPE_IN_USE",
            message="Document type is used and cannot be deleted.",
            details={
                "document_type_id": document_type_id_value,
                "blocking_dependencies": tuple(usage.blocking_dependencies),
                "usage": usage.as_details(),
            },
        )
        self.document_type_id = document_type_id_value


class DocumentTypeValidationError(ValidationApplicationError):
    """Raised when document type command input is invalid."""

    def __init__(self, *, message: str) -> None:
        super().__init__(
            code="DOCUMENT_TYPE_VALIDATION_ERROR",
            message=message,
        )
