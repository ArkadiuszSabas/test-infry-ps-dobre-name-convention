"""System route registration for the DocMind.ai worker service."""

from fastapi import APIRouter

from docmind_backend_runtime import RuntimeSettings
from docmind_worker.api.system import create_system_router
from docmind_worker.bootstrap.dependencies.system import build_service_info_service_dependency


def get_system_router(*, settings: RuntimeSettings) -> APIRouter:
    """Return the system router."""
    return create_system_router(
        service_info_dependency=build_service_info_service_dependency(settings),
    )
