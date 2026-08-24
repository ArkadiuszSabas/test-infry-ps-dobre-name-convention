"""Route registration for internal OCR pipeline endpoints."""

from fastapi import APIRouter

from docmind_backend_runtime import RuntimeSettings
from docmind_llmmagic.api.internal_ocr.router import (
    create_denied_internal_ocr_router,
    create_internal_ocr_router,
)
from docmind_llmmagic.bootstrap.dependencies.internal_ocr import (
    get_internal_ocr_access_dependency,
    internal_ocr_access_is_allowed,
)
from docmind_llmmagic.bootstrap.dependencies.pipeline import (
    get_pipeline_definition_compiler,
    get_pipeline_invocation_service,
)


def get_internal_ocr_router(*, runtime_settings: RuntimeSettings) -> APIRouter:
    """Return the internal OCR pipeline router."""

    access_dependency = get_internal_ocr_access_dependency(runtime_settings)
    if not internal_ocr_access_is_allowed(runtime_settings):
        return create_denied_internal_ocr_router(access_dependency=access_dependency)

    return create_internal_ocr_router(
        compiler_dependency=get_pipeline_definition_compiler,
        invocation_dependency=get_pipeline_invocation_service,
        access_dependency=access_dependency,
    )
