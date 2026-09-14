"""Workspace registry identities, lifecycle, and provisioning records."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class WorkspaceLifecycle(StrEnum):
    """Lifecycle controlled by future workspace administration use cases."""

    REGISTERED = "registered"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETING = "deleting"
    DELETED = "deleted"


class WorkspaceSchemaState(StrEnum):
    """Server-owned physical-schema readiness."""

    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class ProvisioningRequestStatus(StrEnum):
    """Durable outcome for one provisioning attempt."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Workspace:
    """Stable technical data-area identity, separate from its directory entry."""

    id: UUID
    directory_dictionary_id: UUID | None
    directory_entry_id: UUID | None
    schema_name: str
    schema_layout: str
    storage_prefix: str
    lifecycle: WorkspaceLifecycle
    schema_state: WorkspaceSchemaState
    schema_revision: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if (self.directory_dictionary_id is None) != (self.directory_entry_id is None):
            raise ValueError("Workspace directory dictionary and entry bindings must be paired.")
        if self.schema_name != f"ws_{self.id.hex}":
            raise ValueError("Workspace schema_name must be derived from the workspace ID.")
        if self.schema_layout != "dedicated_schema":
            raise ValueError("Workspace schema_layout must be dedicated_schema.")
        if self.storage_prefix != f"workspaces/{self.id}":
            raise ValueError("Workspace storage_prefix must be derived from the workspace ID.")
        if self.created_at > self.updated_at:
            raise ValueError("Workspace updated_at cannot be before created_at.")
        if self.schema_state is WorkspaceSchemaState.READY and not self.schema_revision:
            raise ValueError("Ready workspace schemas require an installed revision.")


@dataclass(frozen=True, slots=True)
class ProvisioningRequest:
    """One durable, idempotent request for a workspace schema preparation attempt."""

    id: UUID
    workspace_id: UUID
    idempotency_key: str
    payload_fingerprint: str
    target_revision: str
    status: ProvisioningRequestStatus
    result_code: str | None
    result_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    def __post_init__(self) -> None:
        if not self.idempotency_key.strip() or len(self.idempotency_key) > 128:
            raise ValueError("Provisioning idempotency_key must contain at most 128 characters.")
        if len(self.payload_fingerprint) != 64:
            raise ValueError("Provisioning payload_fingerprint must be a SHA-256 digest.")
        if not self.target_revision.strip() or len(self.target_revision) > 128:
            raise ValueError("Provisioning target_revision must contain at most 128 characters.")
        if self.created_at > self.updated_at:
            raise ValueError("Provisioning request updated_at cannot be before created_at.")
        if self.status is ProvisioningRequestStatus.PENDING and self.completed_at is not None:
            raise ValueError("Pending provisioning requests cannot have completed_at.")
        if self.status is not ProvisioningRequestStatus.PENDING and self.completed_at is None:
            raise ValueError("Completed provisioning requests require completed_at.")
