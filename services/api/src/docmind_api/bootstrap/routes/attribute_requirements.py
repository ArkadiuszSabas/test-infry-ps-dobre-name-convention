"""Attribute requirement matrix route registration."""

from fastapi import APIRouter

from docmind_api.api.attribute_requirements.router import create_attribute_requirements_router
from docmind_api.bootstrap.dependencies.attribute_requirements import (
    get_attribute_requirement_matrix_service,
)
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.settings import BrowserSecuritySettings


def get_attribute_requirements_router(
    *,
    browser_security_settings: BrowserSecuritySettings,
) -> APIRouter:
    """Return the attribute requirement matrix router."""

    return create_attribute_requirements_router(
        attribute_requirement_matrix_dependency=get_attribute_requirement_matrix_service,
        user_session_service_dependency=get_user_session_service,
        allowed_browser_origins=browser_security_settings.allowed_origins,
    )
