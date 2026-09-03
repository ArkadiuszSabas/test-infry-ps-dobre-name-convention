"""OCR pipeline run route registration."""

from fastapi import APIRouter

from docmind_api.api.ocr_pipeline_runs.router import create_ocr_pipeline_runs_router
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.bootstrap.dependencies.ocr_pipeline_runs import (
    get_admin_ocr_run_read_service,
    get_ocr_event_run_completer,
    get_ocr_pipeline_run_repository,
    get_ocr_pipeline_run_service,
    get_ocr_pipeline_run_settings,
    get_ocr_pipeline_run_starter,
)
from docmind_api.settings import BrowserSecuritySettings


def get_ocr_pipeline_runs_router(
    *,
    browser_security_settings: BrowserSecuritySettings,
) -> APIRouter:
    """Return the OCR pipeline run router."""

    return create_ocr_pipeline_runs_router(
        ocr_pipeline_run_starter_dependency=get_ocr_pipeline_run_starter,
        ocr_pipeline_run_service_dependency=get_ocr_pipeline_run_service,
        ocr_pipeline_run_repository_dependency=get_ocr_pipeline_run_repository,
        ocr_event_run_completer_dependency=get_ocr_event_run_completer,
        ocr_pipeline_run_settings_dependency=get_ocr_pipeline_run_settings,
        user_session_service_dependency=get_user_session_service,
        allowed_browser_origins=browser_security_settings.allowed_origins,
        admin_ocr_run_read_service_dependency=get_admin_ocr_run_read_service,
    )
