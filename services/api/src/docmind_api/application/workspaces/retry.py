"""Durable workspace-provisioning retry orchestration."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from docmind_api.application.workspaces.commands import (
    RetryWorkspaceProvisioningCommand,
    WorkspaceDetails,
)
from docmind_api.application.workspaces.errors import (
    WorkspaceIdempotencyConflictError,
    WorkspaceProvisioningNotRetryableError,
)
from docmind_api.application.workspaces.ports import (
    Clock,
    WorkspaceDirectoryConfiguration,
    WorkspaceIdFactory,
    WorkspaceRepository,
)
from docmind_api.application.workspaces.read import require_workspace
from docmind_api.application.workspaces.registration import (
    require_available_configuration,
    retry_fingerprint,
)
from docmind_api.domain.workspaces.models import (
    ProvisioningRequest,
    ProvisioningRequestStatus,
    WorkspaceLifecycle,
    WorkspaceSchemaState,
)


async def retry_workspace_provisioning(
    *,
    repository: WorkspaceRepository,
    configuration: WorkspaceDirectoryConfiguration,
    clock: Clock,
    id_factory: WorkspaceIdFactory,
    get_details: Callable[[UUID], Awaitable[WorkspaceDetails]],
    command: RetryWorkspaceProvisioningCommand,
) -> WorkspaceDetails:
    """Record a retry request while leaving schema readiness to the migrator."""

    require_available_configuration(configuration)
    workspace = await require_workspace(
        repository=repository,
        workspace_id=command.workspace_id,
        for_update=True,
    )
    existing = await repository.get_request_by_idempotency_key(command.idempotency_key)
    if existing is not None:
        fingerprint = retry_fingerprint(workspace.id, existing.target_revision)
        if existing.payload_fingerprint != fingerprint or existing.workspace_id != workspace.id:
            raise WorkspaceIdempotencyConflictError(idempotency_key=command.idempotency_key)
        return await get_details(existing.workspace_id)

    requests = await repository.list_requests(workspace.id)
    latest = requests[0] if requests else None
    if latest is None or latest.status is not ProvisioningRequestStatus.FAILED:
        raise WorkspaceProvisioningNotRetryableError(workspace_id=workspace.id)
    if (
        workspace.lifecycle is not WorkspaceLifecycle.REGISTERED
        or workspace.schema_state is not WorkspaceSchemaState.FAILED
        or workspace.schema_revision is not None
    ):
        raise WorkspaceProvisioningNotRetryableError(workspace_id=workspace.id)

    timestamp = clock.now()
    fingerprint = retry_fingerprint(workspace.id, latest.target_revision)
    request = ProvisioningRequest(
        id=id_factory.new_id(),
        workspace_id=workspace.id,
        idempotency_key=command.idempotency_key,
        payload_fingerprint=fingerprint,
        target_revision=latest.target_revision,
        status=ProvisioningRequestStatus.PENDING,
        result_code=None,
        result_message=None,
        created_at=timestamp,
        updated_at=timestamp,
        completed_at=None,
    )
    if not await repository.create_retry_request(request):
        existing = await repository.get_request_by_idempotency_key(command.idempotency_key)
        if (
            existing is None
            or existing.payload_fingerprint != fingerprint
            or existing.workspace_id != workspace.id
        ):
            raise WorkspaceIdempotencyConflictError(idempotency_key=command.idempotency_key)
    return await get_details(workspace.id)
