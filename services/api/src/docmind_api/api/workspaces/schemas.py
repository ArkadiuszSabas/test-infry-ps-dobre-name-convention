"""Pydantic schemas for workspace registry administration endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from docmind_api.domain.dictionaries.models import (
    DICTIONARY_ENTRY_LABEL_MAX_LENGTH,
    DICTIONARY_ID_MAX_LENGTH,
    DictionaryEntryScalar,
)
from docmind_api.domain.workspaces.models import (
    ProvisioningRequestStatus,
    WorkspaceLifecycle,
    WorkspaceSchemaState,
)


class NewWorkspaceDirectoryEntryRequest(BaseModel):
    """New dynamic directory entry supplied for a workspace registration."""

    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(min_length=1, max_length=DICTIONARY_ID_MAX_LENGTH)
    label: str = Field(min_length=1, max_length=DICTIONARY_ENTRY_LABEL_MAX_LENGTH)
    values: dict[str, DictionaryEntryScalar] = Field(default_factory=dict)
    sort_order: int | None = Field(default=None, ge=0)


class RegisterWorkspaceRequest(BaseModel):
    """Register a workspace by creating or adopting its configured directory entry."""

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=1, max_length=128)
    directory_entry_id: UUID | None = None
    new_directory_entry: NewWorkspaceDirectoryEntryRequest | None = None

    @model_validator(mode="after")
    def require_one_directory_entry_source(self) -> RegisterWorkspaceRequest:
        if (self.directory_entry_id is None) == (self.new_directory_entry is None):
            raise ValueError(
                "Provide exactly one of directory_entry_id or new_directory_entry.",
            )
        return self


class UpdateWorkspaceDirectoryEntryRequest(BaseModel):
    """Descriptive updates for a bound dynamic directory entry."""

    model_config = ConfigDict(extra="forbid")

    external_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=DICTIONARY_ID_MAX_LENGTH,
    )
    label: str | None = Field(
        default=None,
        min_length=1,
        max_length=DICTIONARY_ENTRY_LABEL_MAX_LENGTH,
    )
    values: dict[str, DictionaryEntryScalar] | None = None
    sort_order: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_any_field(self) -> UpdateWorkspaceDirectoryEntryRequest:
        if not self.model_fields_set:
            raise ValueError("Provide at least one descriptive directory field.")
        return self


class RetryWorkspaceProvisioningRequest(BaseModel):
    """New idempotency key for a controlled retry after a failed request."""

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=1, max_length=128)


class WorkspaceDirectoryEntrySchema(BaseModel):
    """Safe business data from the directory entry bound to a workspace."""

    id: UUID
    dictionary_id: UUID
    external_id: str
    label: str
    values: dict[str, DictionaryEntryScalar]
    sort_order: int | None


class WorkspaceProvisioningRequestSchema(BaseModel):
    """Safe status for one durable provisioning request."""

    id: UUID
    target_revision: str
    status: ProvisioningRequestStatus
    result_code: str | None
    result_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class WorkspaceSchema(BaseModel):
    """Workspace lifecycle and schema-readiness status without DDL controls."""

    id: UUID
    lifecycle: WorkspaceLifecycle
    schema_state: WorkspaceSchemaState
    schema_revision: str | None
    directory_entry: WorkspaceDirectoryEntrySchema | None
    provisioning_requests: list[WorkspaceProvisioningRequestSchema]
    created_at: datetime
    updated_at: datetime


class WorkspaceEnvelope(BaseModel):
    """Standard API response envelope for one workspace."""

    data: WorkspaceSchema
    meta: dict[str, str] = Field(default_factory=dict)


class WorkspaceListPayload(BaseModel):
    """List payload for profile-configured workspace administration."""

    workspaces: list[WorkspaceSchema]


class WorkspaceListEnvelope(BaseModel):
    """Standard API response envelope for workspace lists."""

    data: WorkspaceListPayload
    meta: dict[str, int] = Field(default_factory=dict)
