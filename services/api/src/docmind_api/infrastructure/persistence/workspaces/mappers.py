"""Mapping helpers for workspace registry persistence rows."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from docmind_api.domain.workspaces.models import (
    ProvisioningRequest,
    ProvisioningRequestStatus,
    Workspace,
    WorkspaceLifecycle,
    WorkspaceSchemaState,
)


def workspace_from_row(row: Mapping[Any, Any]) -> Workspace:
    """Map a PostgreSQL workspace row to the domain model."""

    return Workspace(
        id=UUID(str(row["id"])),
        directory_dictionary_id=_uuid_or_none(row["directory_dictionary_id"]),
        directory_entry_id=_uuid_or_none(row["directory_entry_id"]),
        schema_name=str(row["schema_name"]),
        schema_layout=str(row["schema_layout"]),
        storage_prefix=str(row["storage_prefix"]),
        lifecycle=WorkspaceLifecycle(str(row["lifecycle"])),
        schema_state=WorkspaceSchemaState(str(row["schema_state"])),
        schema_revision=_str_or_none(row["schema_revision"]),
        created_at=_datetime_value(row["created_at"]),
        updated_at=_datetime_value(row["updated_at"]),
    )


def provisioning_request_from_row(row: Mapping[Any, Any]) -> ProvisioningRequest:
    """Map a PostgreSQL provisioning-request row to the domain model."""

    return ProvisioningRequest(
        id=UUID(str(row["id"])),
        workspace_id=UUID(str(row["workspace_id"])),
        idempotency_key=str(row["idempotency_key"]),
        payload_fingerprint=str(row["payload_fingerprint"]),
        target_revision=str(row["target_revision"]),
        status=ProvisioningRequestStatus(str(row["status"])),
        result_code=_str_or_none(row["result_code"]),
        result_message=_str_or_none(row["result_message"]),
        created_at=_datetime_value(row["created_at"]),
        updated_at=_datetime_value(row["updated_at"]),
        completed_at=_datetime_or_none(row["completed_at"]),
    )


def _uuid_or_none(value: object) -> UUID | None:
    return UUID(str(value)) if value is not None else None


def _str_or_none(value: object) -> str | None:
    return str(value) if value is not None else None


def _datetime_value(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("Expected a datetime database value")
    return value


def _datetime_or_none(value: object) -> datetime | None:
    return _datetime_value(value) if value is not None else None
