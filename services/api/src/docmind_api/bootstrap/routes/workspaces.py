"""Workspace registry route registration."""

from fastapi import APIRouter

from docmind_api.api.workspaces.router import create_workspaces_router
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.bootstrap.dependencies.workspaces import get_workspace_registry_service
from docmind_api.settings import BrowserSecuritySettings


def get_workspaces_router(
    *,
    browser_security_settings: BrowserSecuritySettings,
) -> APIRouter:
    """Return workspace administration routes backed by profile configuration."""

    return create_workspaces_router(
        workspace_registry_dependency=get_workspace_registry_service,
        user_session_service_dependency=get_user_session_service,
        allowed_browser_origins=browser_security_settings.allowed_origins,
    )
