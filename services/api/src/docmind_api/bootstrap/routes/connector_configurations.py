"""Register API-owned connector configuration administration routes."""

from docmind_api.api.connector_configurations.router import create_connector_configurations_router
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.bootstrap.dependencies.connector_configurations import (
    get_connector_configuration_service,
)
from docmind_api.settings import BrowserSecuritySettings


def get_connector_configurations_router(*, browser_security_settings: BrowserSecuritySettings):
    return create_connector_configurations_router(
        configuration_service_dependency=get_connector_configuration_service,
        csrf_token_validator_dependency=get_user_session_service,
        allowed_browser_origins=browser_security_settings.allowed_origins,
    )
