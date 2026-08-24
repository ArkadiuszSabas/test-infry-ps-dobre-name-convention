"""System route registration for the DocMind.ai API service."""

from fastapi import APIRouter

from docmind_api.api.system import create_system_router
from docmind_api.bootstrap.dependencies.system import build_service_info_service_dependency
from docmind_backend_runtime import RuntimeSettings


def get_system_router(*, settings: RuntimeSettings) -> APIRouter:
    """Return the system router."""
    return create_system_router(
        service_info_dependency=build_service_info_service_dependency(settings),
    )
