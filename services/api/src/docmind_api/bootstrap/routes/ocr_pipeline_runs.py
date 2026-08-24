"""OCR pipeline run route registration."""

from fastapi import APIRouter

from docmind_api.api.ocr_pipeline_runs.router import create_ocr_pipeline_runs_router
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.bootstrap.dependencies.ocr_pipeline_runs import (
    get_ocr_pipeline_run_dispatcher,
    get_ocr_pipeline_run_scheduler,
    get_ocr_pipeline_run_service,
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
        ocr_pipeline_run_dispatcher_dependency=get_ocr_pipeline_run_dispatcher,
        ocr_pipeline_run_scheduler_dependency=get_ocr_pipeline_run_scheduler,
        user_session_service_dependency=get_user_session_service,
        allowed_browser_origins=browser_security_settings.allowed_origins,
    )
