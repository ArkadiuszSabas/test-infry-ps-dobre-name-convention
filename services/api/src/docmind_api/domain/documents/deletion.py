"""Minimal durable state for permanent document deletion."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from docmind_core.connectors import ConnectorDocumentDeletionPolicy


class DocumentDeletionStage(StrEnum):
    """Last durably completed deletion stage."""

    REQUESTED = "requested"
    CONNECTOR_PREPARED = "connector_prepared"
    CONTENT_DELETED = "content_deleted"
    COMPLETED = "completed"


class DocumentDeletionFailureStage(StrEnum):
    """Stage whose failure currently blocks progress."""

    CONNECTOR = "connector"
    CONTENT = "content"
    DATABASE = "database"


class DocumentDeletionState(StrEnum):
    """Safe client-facing state derived from durable operation fields."""

    IN_PROGRESS = "in_progress"
    RETRYABLE = "retryable"
    BLOCKED = "blocked"
    AMBIGUOUS = "ambiguous"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class DocumentDeletionOperation:
    """Payload-free deletion tombstone retained after the document is purged."""

    operation_id: UUID
    document_id: UUID
    stage: DocumentDeletionStage
    connector_instance_id: str | None
    policy: ConnectorDocumentDeletionPolicy | None
    warning_code: str | None
    failure_stage: DocumentDeletionFailureStage | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    @property
    def state(self) -> DocumentDeletionState:
        """Map durable fields to the stable browser reconciliation state."""

        if self.stage is DocumentDeletionStage.COMPLETED:
            return DocumentDeletionState.COMPLETED
        if self.error_code == "DOCUMENT_DELETE_AMBIGUOUS":
            return DocumentDeletionState.AMBIGUOUS
        if self.error_code in {
            "DOCUMENT_DELETE_BLOCKED",
            "DOCUMENT_DELETE_CONNECTOR_HANDLER_REQUIRED",
        }:
            return DocumentDeletionState.BLOCKED
        if self.error_code is not None:
            return DocumentDeletionState.RETRYABLE
        return DocumentDeletionState.IN_PROGRESS
