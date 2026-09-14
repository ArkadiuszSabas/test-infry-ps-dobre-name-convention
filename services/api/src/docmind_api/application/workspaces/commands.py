"""Workspace registry use-case commands and read models."""

from dataclasses import dataclass
from uuid import UUID

from docmind_api.domain.dictionaries.models import DictionaryEntryScalar
from docmind_api.domain.workspaces.models import ProvisioningRequest, Workspace


@dataclass(frozen=True, slots=True)
class NewDirectoryEntry:
    """Business data for a new entry in the configured directory dictionary."""

    external_id: str
    label: str
    values: dict[str, DictionaryEntryScalar]
    sort_order: int | None = None


@dataclass(frozen=True, slots=True)
class RegisterWorkspaceCommand:
    """Register or adopt one configured directory entry as a workspace."""

    idempotency_key: str
    directory_entry_id: UUID | None = None
    new_directory_entry: NewDirectoryEntry | None = None


@dataclass(frozen=True, slots=True)
class UpdateWorkspaceDirectoryEntryCommand:
    """Edit only business data belonging to a bound directory entry."""

    workspace_id: UUID
    external_id: str | None = None
    label: str | None = None
    values: dict[str, DictionaryEntryScalar] | None = None
    sort_order: int | None = None


@dataclass(frozen=True, slots=True)
class RetryWorkspaceProvisioningCommand:
    """Request one new durable provisioning attempt after a recorded failure."""

    workspace_id: UUID
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class WorkspaceDetails:
    """Registry read model with current directory data and request history."""

    workspace: Workspace
    directory_entry_id: UUID | None
    directory_dictionary_id: UUID | None
    directory_external_id: str | None
    directory_label: str | None
    directory_values: dict[str, DictionaryEntryScalar] | None
    directory_sort_order: int | None
    requests: tuple[ProvisioningRequest, ...]
