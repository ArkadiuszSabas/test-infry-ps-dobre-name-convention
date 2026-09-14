"""HTTP response mappers for workspace registry read models."""

from docmind_api.api.workspaces.schemas import (
    WorkspaceDirectoryEntrySchema,
    WorkspaceProvisioningRequestSchema,
    WorkspaceSchema,
)
from docmind_api.application.workspaces.commands import WorkspaceDetails


def to_workspace_schema(details: WorkspaceDetails) -> WorkspaceSchema:
    """Map the application read model without exposing schema names or storage prefixes."""

    directory_entry = None
    if details.directory_entry_id is not None and details.directory_dictionary_id is not None:
        directory_entry = WorkspaceDirectoryEntrySchema(
            id=details.directory_entry_id,
            dictionary_id=details.directory_dictionary_id,
            external_id=details.directory_external_id or "",
            label=details.directory_label or "",
            values=details.directory_values or {},
            sort_order=details.directory_sort_order,
        )
    return WorkspaceSchema(
        id=details.workspace.id,
        lifecycle=details.workspace.lifecycle,
        schema_state=details.workspace.schema_state,
        schema_revision=details.workspace.schema_revision,
        directory_entry=directory_entry,
        provisioning_requests=[
            WorkspaceProvisioningRequestSchema(
                id=request.id,
                target_revision=request.target_revision,
                status=request.status,
                result_code=request.result_code,
                result_message=request.result_message,
                created_at=request.created_at,
                updated_at=request.updated_at,
                completed_at=request.completed_at,
            )
            for request in details.requests
        ],
        created_at=details.workspace.created_at,
        updated_at=details.workspace.updated_at,
    )
