"""Application port for durable connector approved-document archive state."""

from typing import Protocol
from uuid import UUID

from docmind_core.connectors import (
    ConnectorDocumentArchive,
    ConnectorDocumentArchiveFailureStage,
    ConnectorDocumentArchivePlan,
)


class ConnectorDocumentArchiveReader(Protocol):
    """Reads durable connector archive state for document presentation."""

    async def get(self, document_id: UUID) -> ConnectorDocumentArchive | None: ...

    async def get_succeeded_web_urls(
        self,
        document_ids: tuple[UUID, ...],
    ) -> dict[UUID, str]: ...


class ConnectorDocumentArchiveRepository(ConnectorDocumentArchiveReader, Protocol):
    """Persists one retry-stable archive operation per approved document."""

    async def reserve(
        self,
        plan: ConnectorDocumentArchivePlan,
    ) -> ConnectorDocumentArchive: ...

    async def succeed(
        self,
        plan: ConnectorDocumentArchivePlan,
        *,
        drive_item_id: str,
        web_url: str,
    ) -> ConnectorDocumentArchive: ...

    async def fail(
        self,
        plan: ConnectorDocumentArchivePlan,
        *,
        error_code: str,
        failure_stage: ConnectorDocumentArchiveFailureStage,
    ) -> ConnectorDocumentArchive: ...

    async def cancel(
        self,
        document_id: UUID,
        *,
        error_code: str,
    ) -> ConnectorDocumentArchive | None: ...
