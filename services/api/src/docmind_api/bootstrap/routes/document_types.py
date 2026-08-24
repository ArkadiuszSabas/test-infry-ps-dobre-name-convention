"""Document type catalog route registration."""

from fastapi import APIRouter

from docmind_api.api.document_types.router import create_document_types_router
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.bootstrap.dependencies.document_types import get_document_type_catalog_service
from docmind_api.settings import BrowserSecuritySettings


def get_document_types_router(
    *,
    browser_security_settings: BrowserSecuritySettings,
) -> APIRouter:
    """Return the document type catalog router."""

    return create_document_types_router(
        document_type_catalog_dependency=get_document_type_catalog_service,
        user_session_service_dependency=get_user_session_service,
        allowed_browser_origins=browser_security_settings.allowed_origins,
    )
