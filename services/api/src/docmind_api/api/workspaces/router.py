"""Thin FastAPI routes for workspace registry administration."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from docmind_api.api.auth.dependencies import (
    require_cookie_csrf_protection,
    require_permissions,
)
from docmind_api.api.workspaces.mappers import to_workspace_schema
from docmind_api.api.workspaces.schemas import (
    RegisterWorkspaceRequest,
    RetryWorkspaceProvisioningRequest,
    UpdateWorkspaceDirectoryEntryRequest,
    WorkspaceEnvelope,
    WorkspaceListEnvelope,
    WorkspaceListPayload,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.application.workspaces.commands import (
    NewDirectoryEntry,
    RegisterWorkspaceCommand,
    RetryWorkspaceProvisioningCommand,
    UpdateWorkspaceDirectoryEntryCommand,
)
from docmind_api.application.workspaces.service import WorkspaceRegistryService
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission


def create_workspaces_router(
    *,
    workspace_registry_dependency: Callable[..., WorkspaceRegistryService],
    user_session_service_dependency: Callable[..., UserSessionService],
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create profile-configured workspace administration routes."""

    router = APIRouter(prefix="/workspaces", tags=["workspaces"])
    require_admin_settings_manage = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def register_workspace(
        request: RegisterWorkspaceRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        registry: Annotated[
            WorkspaceRegistryService,
            Depends(workspace_registry_dependency),
        ],
    ) -> WorkspaceEnvelope:
        new_entry = request.new_directory_entry
        details = await registry.register(
            RegisterWorkspaceCommand(
                idempotency_key=request.idempotency_key,
                directory_entry_id=request.directory_entry_id,
                new_directory_entry=(
                    NewDirectoryEntry(
                        external_id=new_entry.external_id,
                        label=new_entry.label,
                        values=new_entry.values,
                        sort_order=new_entry.sort_order,
                    )
                    if new_entry is not None
                    else None
                ),
            ),
        )
        return WorkspaceEnvelope(data=to_workspace_schema(details))

    async def list_workspaces(
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        registry: Annotated[
            WorkspaceRegistryService,
            Depends(workspace_registry_dependency),
        ],
    ) -> WorkspaceListEnvelope:
        details = await registry.list_details()
        workspaces = [to_workspace_schema(item) for item in details]
        return WorkspaceListEnvelope(
            data=WorkspaceListPayload(workspaces=workspaces),
            meta={"total": len(workspaces)},
        )

    async def get_workspace(
        workspace_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        registry: Annotated[
            WorkspaceRegistryService,
            Depends(workspace_registry_dependency),
        ],
    ) -> WorkspaceEnvelope:
        return WorkspaceEnvelope(data=to_workspace_schema(await registry.get_details(workspace_id)))

    async def update_workspace_directory_entry(
        workspace_id: UUID,
        request: UpdateWorkspaceDirectoryEntryRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        registry: Annotated[
            WorkspaceRegistryService,
            Depends(workspace_registry_dependency),
        ],
    ) -> WorkspaceEnvelope:
        details = await registry.update_directory_entry(
            UpdateWorkspaceDirectoryEntryCommand(
                workspace_id=workspace_id,
                external_id=request.external_id,
                label=request.label,
                values=request.values,
                sort_order=request.sort_order,
            ),
        )
        return WorkspaceEnvelope(data=to_workspace_schema(details))

    async def retry_workspace_provisioning(
        workspace_id: UUID,
        request: RetryWorkspaceProvisioningRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        registry: Annotated[
            WorkspaceRegistryService,
            Depends(workspace_registry_dependency),
        ],
    ) -> WorkspaceEnvelope:
        details = await registry.retry_provisioning(
            RetryWorkspaceProvisioningCommand(
                workspace_id=workspace_id,
                idempotency_key=request.idempotency_key,
            ),
        )
        return WorkspaceEnvelope(data=to_workspace_schema(details))

    router.add_api_route(
        "",
        register_workspace,
        methods=["POST"],
        status_code=HTTPStatus.CREATED,
        response_model=WorkspaceEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route("", list_workspaces, methods=["GET"], response_model=WorkspaceListEnvelope)
    router.add_api_route(
        "/{workspace_id}", get_workspace, methods=["GET"], response_model=WorkspaceEnvelope
    )
    router.add_api_route(
        "/{workspace_id}",
        update_workspace_directory_entry,
        methods=["PATCH"],
        response_model=WorkspaceEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{workspace_id}/provisioning-requests",
        retry_workspace_provisioning,
        methods=["POST"],
        status_code=HTTPStatus.ACCEPTED,
        response_model=WorkspaceEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    return router
