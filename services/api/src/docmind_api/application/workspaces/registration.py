"""Validation and stable payload helpers for workspace registration."""

import hashlib
import json
from uuid import UUID

from docmind_api.application.workspaces.commands import RegisterWorkspaceCommand
from docmind_api.application.workspaces.errors import (
    WorkspaceAdministrationUnavailableError,
    WorkspaceDirectoryConfigurationError,
    WorkspaceIdempotencyConflictError,
)
from docmind_api.application.workspaces.ports import WorkspaceDirectoryConfiguration


def require_available_configuration(configuration: WorkspaceDirectoryConfiguration) -> None:
    """Reject workspace administration outside an enabled profile."""

    if not configuration.is_available:
        raise WorkspaceAdministrationUnavailableError()


def validate_registration_shape(command: RegisterWorkspaceCommand) -> None:
    """Validate the mutually exclusive directory-entry sources."""

    if not command.idempotency_key.strip() or len(command.idempotency_key) > 128:
        raise WorkspaceIdempotencyConflictError(idempotency_key=command.idempotency_key)
    if (command.directory_entry_id is None) == (command.new_directory_entry is None):
        raise WorkspaceDirectoryConfigurationError()


def registration_fingerprint(command: RegisterWorkspaceCommand) -> str:
    """Return a stable fingerprint for registration idempotency."""

    new_entry = command.new_directory_entry
    return fingerprint(
        {
            "directory_entry_id": str(command.directory_entry_id)
            if command.directory_entry_id
            else None,
            "new_directory_entry": (
                {
                    "external_id": new_entry.external_id.strip() if new_entry else None,
                    "label": new_entry.label.strip() if new_entry else None,
                    "values": new_entry.values if new_entry else None,
                    "sort_order": new_entry.sort_order if new_entry else None,
                }
                if new_entry is not None
                else None
            ),
        },
    )


def retry_fingerprint(workspace_id: UUID, target_revision: str) -> str:
    """Return a stable fingerprint for provisioning retry idempotency."""

    return fingerprint({"workspace_id": str(workspace_id), "target_revision": target_revision})


def schema_name(workspace_id: UUID) -> str:
    """Return the reserved dedicated-schema name for a workspace."""

    return f"ws_{workspace_id.hex}"


def fingerprint(payload: object) -> str:
    """Serialize payload deterministically and hash it."""

    serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
