"""Route registration for the DocMind.ai worker service."""

from fastapi import APIRouter

from docmind_backend_runtime import RuntimeSettings
from docmind_worker.bootstrap.routes.dapr_smoke import get_dapr_smoke_router
from docmind_worker.bootstrap.routes.health import get_health_router
from docmind_worker.bootstrap.routes.system import get_system_router


def get_worker_routers(*, settings: RuntimeSettings) -> tuple[APIRouter, ...]:
    """Return routers registered by the worker service."""
    routers = [
        get_system_router(settings=settings),
        get_health_router(),
    ]
    if settings.environment in {"local", "test"}:
        routers.append(get_dapr_smoke_router())

    return tuple(routers)
