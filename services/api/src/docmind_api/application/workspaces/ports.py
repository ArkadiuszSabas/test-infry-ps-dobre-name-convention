"""Ports for workspace-registry persistence and profile selection."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from docmind_api.domain.dictionaries.models import DictionaryEntry
from docmind_api.domain.workspaces.models import ProvisioningRequest, Workspace


@dataclass(frozen=True, slots=True)
class WorkspaceDirectoryConfiguration:
    """The active profile's workspace-directory selection."""

    dictionary_external_id: str | None = None
    administration_enabled: bool = False

    @property
    def is_available(self) -> bool:
        return self.administration_enabled and self.dictionary_external_id is not None


class WorkspaceRegistrationWriteResult(StrEnum):
    """Outcome of an atomic registration attempt."""

    CREATED = "created"
    DIRECTORY_ENTRY_EXISTS = "directory_entry_exists"
    DIRECTORY_ENTRY_BOUND = "directory_entry_bound"
    IDEMPOTENCY_KEY_EXISTS = "idempotency_key_exists"


class Clock(Protocol):
    """Port for audit timestamps."""

    def now(self) -> datetime: ...


class WorkspaceIdFactory(Protocol):
    """Port for workspace and provisioning-record UUIDs."""

    def new_id(self) -> UUID: ...


class WorkspaceRepository(Protocol):
    """Persistence operations owned by the workspace registry context."""

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None: ...

    async def get_workspace_for_update(self, workspace_id: UUID) -> Workspace | None: ...

    async def list_workspaces(self) -> tuple[Workspace, ...]: ...

    async def get_workspace_by_directory_entry_id(
        self,
        directory_entry_id: UUID,
    ) -> Workspace | None: ...

    async def list_requests(self, workspace_id: UUID) -> tuple[ProvisioningRequest, ...]: ...

    async def get_request_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> ProvisioningRequest | None: ...

    async def create_registration(
        self,
        *,
        directory_entry: DictionaryEntry | None,
        workspace: Workspace,
        request: ProvisioningRequest,
    ) -> WorkspaceRegistrationWriteResult: ...

    async def create_retry_request(self, request: ProvisioningRequest) -> bool: ...
