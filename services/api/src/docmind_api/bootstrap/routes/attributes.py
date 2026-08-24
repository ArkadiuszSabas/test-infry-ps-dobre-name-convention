"""Attribute definition catalog route registration."""

from fastapi import APIRouter

from docmind_api.api.attributes.categories_router import create_attribute_categories_router
from docmind_api.api.attributes.router import create_attributes_router
from docmind_api.bootstrap.dependencies.attributes import (
    get_attribute_category_catalog_service,
    get_attribute_definition_catalog_service,
)
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.settings import BrowserSecuritySettings


def get_attributes_router(
    *,
    browser_security_settings: BrowserSecuritySettings,
) -> APIRouter:
    """Return the attribute definition catalog router."""

    router = APIRouter()
    router.include_router(
        create_attributes_router(
            attribute_definition_catalog_dependency=get_attribute_definition_catalog_service,
            user_session_service_dependency=get_user_session_service,
            allowed_browser_origins=browser_security_settings.allowed_origins,
        ),
    )
    router.include_router(
        create_attribute_categories_router(
            attribute_category_catalog_dependency=get_attribute_category_catalog_service,
            user_session_service_dependency=get_user_session_service,
            allowed_browser_origins=browser_security_settings.allowed_origins,
        ),
    )
    return router
