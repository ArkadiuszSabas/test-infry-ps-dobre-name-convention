"""Document review route registration."""

from fastapi import APIRouter

from docmind_api.api.document_review.approval_settings_router import (
    create_document_approval_settings_router,
)
from docmind_api.api.document_review.router import create_document_review_router
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.bootstrap.dependencies.document_review import (
    get_document_approval_settings_service,
    get_mock_document_review_service,
    get_unavailable_document_review_service,
)
from docmind_api.settings import BrowserSecuritySettings

_MOCK_REVIEW_ENVIRONMENTS = frozenset({"local", "test", "dev", "sb1", "sb2", "sb3"})


def get_document_review_router(
    *,
    environment: str,
    browser_security_settings: BrowserSecuritySettings,
) -> APIRouter:
    """Return a stable review route with an environment-safe data provider."""

    dependency = (
        get_mock_document_review_service
        if environment in _MOCK_REVIEW_ENVIRONMENTS
        else get_unavailable_document_review_service
    )
    router = APIRouter()
    router.include_router(
        create_document_review_router(
            document_review_service_dependency=dependency,
            user_session_service_dependency=get_user_session_service,
            allowed_browser_origins=browser_security_settings.allowed_origins,
        )
    )
    router.include_router(
        create_document_approval_settings_router(
            settings_service_dependency=get_document_approval_settings_service,
            user_session_service_dependency=get_user_session_service,
            allowed_browser_origins=browser_security_settings.allowed_origins,
        )
    )
    return router
