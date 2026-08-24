"""Document registry route registration."""

from fastapi import APIRouter

from docmind_api.api.documents.router import create_documents_router
from docmind_api.bootstrap.dependencies.auth import get_user_session_service
from docmind_api.bootstrap.dependencies.connectors import get_connector_profile_manifest
from docmind_api.bootstrap.dependencies.document_review import (
    get_document_type_change_review_service,
)
from docmind_api.bootstrap.dependencies.documents import (
    get_document_deletion_service,
    get_document_ingest_settings_dependency,
    get_document_registry_service,
    get_document_type_change_committer,
)
from docmind_api.bootstrap.dependencies.ocr_pipeline_runs import (
    get_ocr_pipeline_run_dispatcher,
    get_ocr_pipeline_run_scheduler,
    get_ocr_pipeline_run_service,
)
from docmind_api.settings import BrowserSecuritySettings


def get_documents_router(
    *,
    browser_security_settings: BrowserSecuritySettings,
) -> APIRouter:
    """Return the document registry router."""

    return create_documents_router(
        document_registry_dependency=get_document_registry_service,
        document_deletion_service_dependency=get_document_deletion_service,
        document_ingest_settings_dependency=get_document_ingest_settings_dependency,
        connector_profile_manifest_dependency=get_connector_profile_manifest,
        user_session_service_dependency=get_user_session_service,
        document_reprocessing_starter_dependency=get_ocr_pipeline_run_service,
        document_reprocessing_dispatcher_dependency=get_ocr_pipeline_run_dispatcher,
        document_reprocessing_scheduler_dependency=get_ocr_pipeline_run_scheduler,
        document_type_change_committer_dependency=get_document_type_change_committer,
        document_type_change_review_service_dependency=get_document_type_change_review_service,
        allowed_browser_origins=browser_security_settings.allowed_origins,
    )
