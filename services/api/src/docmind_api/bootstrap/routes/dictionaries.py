"""Custom dictionary route registration."""

from fastapi import APIRouter

from docmind_api.api.dictionaries.lookup_router import create_dictionary_lookup_router
from docmind_api.api.dictionaries.router import create_dictionaries_router
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.bootstrap.dependencies.dictionaries import (
    get_dictionary_catalog_service,
    get_dictionary_lookup_service,
)
from docmind_api.settings import BrowserSecuritySettings


def get_dictionaries_router(
    *,
    browser_security_settings: BrowserSecuritySettings,
) -> APIRouter:
    """Return the custom dictionary router."""

    router = APIRouter()
    router.include_router(
        create_dictionaries_router(
            dictionary_catalog_dependency=get_dictionary_catalog_service,
            user_session_service_dependency=get_user_session_service,
            allowed_browser_origins=browser_security_settings.allowed_origins,
        ),
    )
    router.include_router(
        create_dictionary_lookup_router(
            dictionary_lookup_dependency=get_dictionary_lookup_service,
        ),
    )
    return router
