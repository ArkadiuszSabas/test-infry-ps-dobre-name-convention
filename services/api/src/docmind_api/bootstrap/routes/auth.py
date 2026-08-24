"""Auth route registration for the DocMind.ai API service."""

from fastapi import APIRouter

from docmind_api.api.auth import create_auth_router
from docmind_api.bootstrap.dependencies.auth import (
    get_complete_entra_oidc_login_use_case,
    get_local_login_use_case,
    get_start_entra_oidc_login_use_case,
    get_user_invitation_service,
    get_user_session_management_service,
    get_user_session_service,
)
from docmind_api.bootstrap.dependencies.auth_user_management import (
    get_own_password_service,
    get_user_administration_service,
)
from docmind_api.settings import BrowserSecuritySettings, load_entra_id_provider_settings


def get_auth_router(*, browser_security_settings: BrowserSecuritySettings) -> APIRouter:
    """Return the auth router."""

    return create_auth_router(
        local_login_use_case_dependency=get_local_login_use_case,
        user_session_service_dependency=get_user_session_service,
        user_session_management_service_dependency=get_user_session_management_service,
        user_invitation_service_dependency=get_user_invitation_service,
        user_administration_service_dependency=get_user_administration_service,
        own_password_service_dependency=get_own_password_service,
        allowed_browser_origins=browser_security_settings.allowed_origins,
        start_entra_oidc_login_use_case_dependency=get_start_entra_oidc_login_use_case,
        complete_entra_oidc_login_use_case_dependency=get_complete_entra_oidc_login_use_case,
        entra_oidc_enabled=load_entra_id_provider_settings().enabled,
    )
