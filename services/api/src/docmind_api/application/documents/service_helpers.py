"""Small pure helpers for document registry service workflows."""

from uuid import UUID

from docmind_api.application.document_types.service import (
    DocumentTypeValidationError,
)
from docmind_api.application.documents.errors import (
    DocumentListValidationError,
)
from docmind_api.application.documents.read_models import DOCUMENT_LIST_MAX_LIMIT
from docmind_api.domain.document_types.models import (
    DocumentType,
    normalize_document_type_external_id,
)
from docmind_api.domain.documents.models import (
    MANUAL_UPLOAD_CONNECTOR,
    MANUAL_UPLOAD_SOURCE,
    DocumentSource,
)


def validated_document_type_id(document_type_id: UUID | str) -> UUID | str:
    try:
        return UUID(str(document_type_id))
    except ValueError as error:
        try:
            return normalize_document_type_external_id(str(document_type_id))
        except ValueError as external_error:
            raise DocumentTypeValidationError(message=str(external_error)) from error


def document_type_name(
    document_type_details: dict[UUID, DocumentType],
    document_type_id: UUID | str,
) -> str:
    normalized_id = coerce_uuid(document_type_id)
    if normalized_id is None:
        return str(document_type_id)

    document_type = document_type_details.get(normalized_id)
    if document_type is None:
        return str(document_type_id)
    return document_type.name


def document_type_external_id(
    document_type_details: dict[UUID, DocumentType],
    document_type_id: UUID | str,
) -> str | None:
    normalized_id = coerce_uuid(document_type_id)
    if normalized_id is None:
        return None

    document_type = document_type_details.get(normalized_id)
    if document_type is None:
        return None
    return document_type.external_id


def coerce_uuid(value: UUID | str) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


def validate_connector_source_is_not_reserved(source: DocumentSource) -> None:
    if source.source == MANUAL_UPLOAD_SOURCE and source.connector == MANUAL_UPLOAD_CONNECTOR:
        raise ValueError(
            "manual_upload source and connector are reserved for browser manual uploads.",
        )


def looks_like_pdf(*, original_filename: str, content: bytes) -> bool:
    return original_filename.lower().endswith(".pdf") and content.startswith(b"%PDF-")


def validate_list_window(*, limit: int, offset: int) -> None:
    if limit < 1 or limit > DOCUMENT_LIST_MAX_LIMIT:
        raise DocumentListValidationError(
            message=(f"Document list limit must be between 1 and {DOCUMENT_LIST_MAX_LIMIT}."),
            details={"limit": limit, "max_limit": DOCUMENT_LIST_MAX_LIMIT},
        )
    if offset < 0:
        raise DocumentListValidationError(
            message="Document list offset cannot be negative.",
            details={"offset": offset},
        )
