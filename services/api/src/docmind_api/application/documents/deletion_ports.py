"""Application ports for permanent document deletion."""

from typing import Protocol
from uuid import UUID

from docmind_api.domain.documents.deletion import (
    DocumentDeletionFailureStage,
    DocumentDeletionOperation,
    DocumentDeletionStage,
)
from docmind_api.domain.documents.models import DocumentRecord
from docmind_core.connectors import (
    ConnectorDocumentDeletionCommand,
    ConnectorDocumentDeletionResult,
)


class DocumentDeletionRepository(Protocol):
    """Durable fence, tombstone, and aggregate purge boundary."""

    async def get(self, document_id: UUID) -> DocumentDeletionOperation | None: ...

    async def get_document(self, document_id: UUID) -> DocumentRecord | None: ...

    async def reserve(
        self,
        document: DocumentRecord,
    ) -> DocumentDeletionOperation: ...

    async def advance(
        self,
        document_id: UUID,
        *,
        stage: DocumentDeletionStage,
        connector_result: ConnectorDocumentDeletionResult | None = None,
    ) -> DocumentDeletionOperation: ...

    async def fail(
        self,
        document_id: UUID,
        *,
        failure_stage: DocumentDeletionFailureStage,
        error_code: str,
        connector_result: ConnectorDocumentDeletionResult | None = None,
    ) -> DocumentDeletionOperation: ...

    async def purge(self, document_id: UUID) -> DocumentDeletionOperation: ...


class DocumentDeletionConnectorGateway(Protocol):
    """Resolve and execute only manifest-selected connector deletion handlers."""

    async def execute(
        self,
        command: ConnectorDocumentDeletionCommand,
    ) -> ConnectorDocumentDeletionResult: ...


class DocumentDeletionCommitter(Protocol):
    """Make each irreversible deletion stage durable before the next one starts."""

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
