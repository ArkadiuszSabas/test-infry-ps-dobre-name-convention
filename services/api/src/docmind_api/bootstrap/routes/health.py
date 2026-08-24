"""Health route registration for the DocMind.ai API service."""

from fastapi import APIRouter

from docmind_api.api.health import create_health_router
from docmind_api.bootstrap.dependencies.health import get_health_service


def get_health_router() -> APIRouter:
    """Return the health router."""
    return create_health_router(
        health_service_dependency=get_health_service,
    )
