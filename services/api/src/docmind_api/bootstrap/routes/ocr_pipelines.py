"""OCR pipeline admin route registration."""

from fastapi import APIRouter

from docmind_api.api.ocr_pipelines.confidence_color_router import (
    create_ocr_confidence_color_router,
)
from docmind_api.api.ocr_pipelines.router import create_ocr_pipelines_router
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.bootstrap.dependencies.ocr_pipelines import (
    get_ocr_confidence_color_settings_service,
    get_ocr_pipeline_admin_service,
)
from docmind_api.settings import BrowserSecuritySettings


def get_ocr_pipelines_router(
    *,
    browser_security_settings: BrowserSecuritySettings,
) -> APIRouter:
    """Return the OCR pipeline admin router."""

    router = APIRouter()
    router.include_router(
        create_ocr_pipelines_router(
            ocr_pipeline_admin_dependency=get_ocr_pipeline_admin_service,
            user_session_service_dependency=get_user_session_service,
            allowed_browser_origins=browser_security_settings.allowed_origins,
        ),
    )
    router.include_router(
        create_ocr_confidence_color_router(
            settings_service_dependency=get_ocr_confidence_color_settings_service,
            user_session_service_dependency=get_user_session_service,
            allowed_browser_origins=browser_security_settings.allowed_origins,
        ),
    )
    return router
