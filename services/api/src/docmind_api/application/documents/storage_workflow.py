"""Storage and registry persistence helpers for document workflows."""

import logging
from collections.abc import Mapping
from uuid import UUID

from docmind_api.application.documents.errors import (
    DocumentAlreadyExistsError,
    DocumentIngestValidationError,
    DocumentStorageWriteError,
)
from docmind_api.application.documents.ports import (
    Clock,
    DocumentContentStorage,
    DocumentContentStorageError,
    DocumentIdFactory,
    DocumentRegistryRepository,
    StoreDocumentContentCommand,
)
from docmind_api.domain.documents.metadata import JsonScalar
from docmind_api.domain.documents.models import (
    DocumentRecord,
    DocumentSource,
    DocumentStatus,
    DocumentUploadActor,
    StorageLocator,
)

_LOGGER = logging.getLogger(__name__)


async def store_and_register_document(
    *,
    repository: DocumentRegistryRepository,
    storage: DocumentContentStorage,
    id_factory: DocumentIdFactory,
    clock: Clock,
    original_filename: str,
    external_id: str | None,
    document_type_id: UUID,
    source: DocumentSource,
    content_type: str | None,
    content: bytes,
    metadata_values: Mapping[str, JsonScalar],
    document_name: str,
    uploaded_by: DocumentUploadActor | None = None,
) -> DocumentRecord:
    document_id = id_factory.new_id()
    try:
        storage_locator = await storage.save(
            StoreDocumentContentCommand(
                document_id=document_id,
                original_filename=original_filename,
                content_type=content_type,
                content=content,
                source=source,
            ),
        )
    except DocumentContentStorageError as error:
        raise DocumentStorageWriteError() from error

    try:
        timestamp = clock.now()
        document = DocumentRecord(
            id=document_id,
            external_id=external_id,
            name=document_name,
            original_filename=original_filename,
            document_type_id=document_type_id,
            status=DocumentStatus.RECEIVED,
            source=source,
            storage_locator=storage_locator,
            content_size_bytes=len(content),
            metadata_values=metadata_values,
            created_at=timestamp,
            updated_at=timestamp,
            uploaded_by=uploaded_by,
        )
        created = await repository.add(document)
        if not created:
            raise DocumentAlreadyExistsError(document_id=str(document.id))
    except ValueError as error:
        await cleanup_stored_content(
            storage=storage,
            document_id=document_id,
            storage_locator=storage_locator,
        )
        raise DocumentIngestValidationError(message=str(error)) from error
    except Exception:
        await cleanup_stored_content(
            storage=storage,
            document_id=document_id,
            storage_locator=storage_locator,
        )
        raise

    return document


async def cleanup_stored_content(
    *,
    storage: DocumentContentStorage,
    document_id: object,
    storage_locator: StorageLocator,
) -> None:
    try:
        await storage.delete(storage_locator)
    except DocumentContentStorageError as error:
        _LOGGER.warning(
            "Stored document cleanup failed after ingest rollback.",
            extra={
                "document_id": str(document_id),
                "storage_error_type": type(error).__name__,
            },
        )
