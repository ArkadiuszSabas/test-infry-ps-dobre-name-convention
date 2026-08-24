"""Application ports for the document registry."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from docmind_api.domain.documents.models import DocumentRecord, DocumentSource, StorageLocator


class Clock(Protocol):
    """Port for obtaining audit timestamps."""

    def now(self) -> datetime: ...


class DocumentIdFactory(Protocol):
    """Port for creating document identifiers."""

    def new_id(self) -> UUID: ...


@dataclass(frozen=True, slots=True)
class StoreDocumentContentCommand:
    """Content and audit metadata sent to object storage."""

    document_id: UUID
    original_filename: str
    content_type: str | None
    content: bytes
    source: DocumentSource


@dataclass(frozen=True, slots=True)
class StoredDocumentContent:
    """Raw content loaded from document storage."""

    content: bytes


class DocumentContentStorageError(Exception):
    """Raised by storage adapters when raw document content IO fails."""


class DocumentContentStorageNotFoundError(DocumentContentStorageError):
    """Raised when a storage locator does not point to an existing object."""


class DocumentContentStorage(Protocol):
    """Port implemented by raw document content storage adapters."""

    async def save(self, command: StoreDocumentContentCommand) -> StorageLocator: ...

    async def load(self, locator: StorageLocator) -> StoredDocumentContent: ...

    async def delete(self, locator: StorageLocator) -> None: ...


class DocumentRegistryRepository(Protocol):
    """Port implemented by document registry persistence adapters."""

    async def add(self, document: DocumentRecord) -> bool: ...

    async def get_by_id(self, document_id: UUID) -> DocumentRecord | None: ...

    async def get_by_id_for_update(self, document_id: UUID) -> DocumentRecord | None: ...

    async def change_document_type(
        self,
        *,
        document_id: UUID,
        document_type_id: UUID,
        actor_id: str,
        reason: str | None,
        changed_at: datetime,
    ) -> DocumentRecord | None: ...

    async def list(
        self,
        *,
        source: str | None = None,
        connector: str | None = None,
        archived: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[DocumentRecord, ...]: ...
