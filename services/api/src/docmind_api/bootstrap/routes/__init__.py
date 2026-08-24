"""Route registration for the DocMind.ai API service."""

from fastapi import APIRouter

from docmind_api.bootstrap.routes.attribute_requirements import get_attribute_requirements_router
from docmind_api.bootstrap.routes.attributes import get_attributes_router
from docmind_api.bootstrap.routes.auth import get_auth_router
from docmind_api.bootstrap.routes.capabilities import get_capabilities_router
from docmind_api.bootstrap.routes.connector_configurations import (
    get_connector_configurations_router,
)
from docmind_api.bootstrap.routes.connectors import get_connector_api_routers
from docmind_api.bootstrap.routes.dapr_smoke import get_dapr_smoke_router
from docmind_api.bootstrap.routes.dashboard import get_dashboard_router
from docmind_api.bootstrap.routes.dictionaries import get_dictionaries_router
from docmind_api.bootstrap.routes.document_review import get_document_review_router
from docmind_api.bootstrap.routes.document_types import get_document_types_router
from docmind_api.bootstrap.routes.documents import get_documents_router
from docmind_api.bootstrap.routes.health import get_health_router
from docmind_api.bootstrap.routes.ocr_pipeline_runs import get_ocr_pipeline_runs_router
from docmind_api.bootstrap.routes.ocr_pipelines import get_ocr_pipelines_router
from docmind_api.bootstrap.routes.system import get_system_router
from docmind_api.bootstrap.routes.system_catalogs import get_system_catalogs_router
from docmind_api.settings import BrowserSecuritySettings
from docmind_backend_runtime import RuntimeSettings


def get_api_routers(
    *,
    settings: RuntimeSettings,
    browser_security_settings: BrowserSecuritySettings,
) -> tuple[APIRouter, ...]:
    """Return routers registered by the API service."""
    routers = [
        get_system_router(settings=settings),
        get_health_router(),
        get_capabilities_router(),
        get_connector_configurations_router(
            browser_security_settings=browser_security_settings,
        ),
        get_auth_router(browser_security_settings=browser_security_settings),
        get_document_types_router(browser_security_settings=browser_security_settings),
        get_attribute_requirements_router(browser_security_settings=browser_security_settings),
        get_attributes_router(browser_security_settings=browser_security_settings),
        get_dictionaries_router(browser_security_settings=browser_security_settings),
        get_system_catalogs_router(browser_security_settings=browser_security_settings),
        get_dashboard_router(),
        get_documents_router(browser_security_settings=browser_security_settings),
        get_document_review_router(
            environment=settings.environment,
            browser_security_settings=browser_security_settings,
        ),
        get_ocr_pipelines_router(browser_security_settings=browser_security_settings),
        get_ocr_pipeline_runs_router(browser_security_settings=browser_security_settings),
        *get_connector_api_routers(),
    ]
    if settings.environment in {"local", "test"}:
        routers.append(get_dapr_smoke_router())

    return tuple(routers)
