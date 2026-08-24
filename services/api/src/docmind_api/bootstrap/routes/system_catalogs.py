"""System catalog route registration."""

from fastapi import APIRouter

from docmind_api.api.system_catalogs.router import create_system_catalogs_router
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.bootstrap.dependencies.document_types import get_document_type_catalog_service
from docmind_api.bootstrap.dependencies.system_catalogs import get_system_catalog_definition_service
from docmind_api.settings import BrowserSecuritySettings


def get_system_catalogs_router(
    *,
    browser_security_settings: BrowserSecuritySettings,
) -> APIRouter:
    """Return the system catalog router."""

    return create_system_catalogs_router(
        system_catalog_definition_dependency=get_system_catalog_definition_service,
        document_type_catalog_dependency=get_document_type_catalog_service,
        user_session_service_dependency=get_user_session_service,
        allowed_browser_origins=browser_security_settings.allowed_origins,
    )
