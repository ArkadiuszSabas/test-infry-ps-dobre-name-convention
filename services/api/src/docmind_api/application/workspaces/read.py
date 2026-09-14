"""Read-model assembly for workspace administration."""

from uuid import UUID

from docmind_api.application.dictionaries.ports import DictionaryRepository
from docmind_api.application.workspaces.commands import WorkspaceDetails
from docmind_api.application.workspaces.errors import WorkspaceNotFoundError
from docmind_api.application.workspaces.ports import WorkspaceRepository


async def get_workspace_details(
    *,
    repository: WorkspaceRepository,
    dictionary_repository: DictionaryRepository,
    workspace_id: UUID,
) -> WorkspaceDetails:
    """Return technical workspace state with its safe directory display data."""

    workspace = await repository.get_workspace(workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError(workspace_id=workspace_id)
    entry = None
    if workspace.directory_entry_id is not None:
        entry = await dictionary_repository.get_entry_by_id(
            workspace.directory_dictionary_id or workspace.directory_entry_id,
            workspace.directory_entry_id,
        )
    requests = await repository.list_requests(workspace.id)
    return WorkspaceDetails(
        workspace=workspace,
        directory_entry_id=UUID(str(entry.id)) if entry is not None else None,
        directory_dictionary_id=workspace.directory_dictionary_id,
        directory_external_id=entry.external_id if entry is not None else None,
        directory_label=entry.label if entry is not None else None,
        directory_values=dict(entry.values) if entry is not None else None,
        directory_sort_order=entry.sort_order if entry is not None else None,
        requests=requests,
    )


async def require_workspace(
    *,
    repository: WorkspaceRepository,
    workspace_id: UUID,
    for_update: bool = False,
):
    """Return an existing workspace, optionally serializing a write workflow."""

    workspace = (
        await repository.get_workspace_for_update(workspace_id)
        if for_update
        else await repository.get_workspace(workspace_id)
    )
    if workspace is None:
        raise WorkspaceNotFoundError(workspace_id=workspace_id)
    return workspace
