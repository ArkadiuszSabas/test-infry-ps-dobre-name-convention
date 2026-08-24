"""FastAPI app factory helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from docmind_backend_runtime.exception_handlers import register_exception_handlers
from docmind_backend_runtime.middleware import install_correlation_id_middleware
from docmind_backend_runtime.observability import configure_observability
from docmind_backend_runtime.settings import RuntimeSettings
from docmind_backend_runtime.telemetry import instrument_fastapi_app

if TYPE_CHECKING:
    from fastapi import APIRouter, FastAPI
    from starlette.types import Lifespan


def create_service_app(
    settings: RuntimeSettings,
    *,
    routers: Iterable[APIRouter] = (),
    lifespan: Lifespan[FastAPI] | None = None,
) -> FastAPI:
    """Create a FastAPI app with DocMind.ai runtime defaults."""

    observability_status = configure_observability(settings)
    from fastapi import FastAPI

    app = FastAPI(title=settings.service_name, lifespan=lifespan)
    instrument_fastapi_app(app, observability_status.azure_monitor)
    install_correlation_id_middleware(app, settings=settings)
    register_exception_handlers(app, settings=settings)

    for router in routers:
        app.include_router(router)

    return app
