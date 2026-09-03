"""FastAPI application bootstrap for the DocMind.ai LLM Magic service."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from docmind_backend_runtime import RuntimeSettings
from docmind_backend_runtime.app import create_service_app
from docmind_llmmagic.bootstrap.dependencies.internal_ocr import build_async_ocr_execution_service
from docmind_llmmagic.bootstrap.dependencies.pipeline import build_pipeline_runtime
from docmind_llmmagic.bootstrap.routes import get_llmmagic_routers
from docmind_llmmagic.settings import get_runtime_settings


def create_app(settings: RuntimeSettings | None = None) -> FastAPI:
    """Create the LLM Magic service FastAPI app."""
    runtime_settings = settings or get_runtime_settings()
    app = create_service_app(
        runtime_settings,
        routers=get_llmmagic_routers(),
        lifespan=_pipeline_lifespan,
    )
    pipeline_runtime = build_pipeline_runtime()
    app.state.pipeline_runtime = pipeline_runtime
    app.state.async_ocr_execution = build_async_ocr_execution_service(
        pipeline_runtime.invocation_service
    )
    return app


@asynccontextmanager
async def _pipeline_lifespan(app: FastAPI) -> AsyncGenerator[None]:
    runtime = app.state.pipeline_runtime
    try:
        yield
    finally:
        await runtime.close()
