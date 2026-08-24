"""FastAPI application bootstrap for the DocMind.ai worker service."""

from fastapi import FastAPI

from docmind_backend_runtime import RuntimeSettings
from docmind_backend_runtime.app import create_service_app
from docmind_worker.bootstrap.routes import get_worker_routers
from docmind_worker.settings import get_runtime_settings


def create_app(settings: RuntimeSettings | None = None) -> FastAPI:
    """Create the worker service FastAPI app."""
    runtime_settings = settings or get_runtime_settings()

    return create_service_app(
        runtime_settings,
        routers=get_worker_routers(settings=runtime_settings),
    )
