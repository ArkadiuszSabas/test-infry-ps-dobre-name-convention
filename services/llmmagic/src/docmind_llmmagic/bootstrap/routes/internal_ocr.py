"""Route registration for internal OCR pipeline endpoints."""

from fastapi import APIRouter

from docmind_llmmagic.api.internal_ocr.router import (
    create_internal_ocr_router,
)
from docmind_llmmagic.bootstrap.dependencies.internal_ocr import (
    get_async_ocr_execution_service,
)
from docmind_llmmagic.bootstrap.dependencies.pipeline import (
    get_pipeline_definition_compiler,
)


def get_internal_ocr_router() -> APIRouter:
    """Return the internal OCR pipeline router."""

    return create_internal_ocr_router(
        compiler_dependency=get_pipeline_definition_compiler,
        execution_dependency=get_async_ocr_execution_service,
    )
