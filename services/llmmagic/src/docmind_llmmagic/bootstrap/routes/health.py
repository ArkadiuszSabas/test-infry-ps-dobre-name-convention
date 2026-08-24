"""Health route registration for the DocMind.ai LLM Magic service."""

from fastapi import APIRouter

from docmind_llmmagic.api.health import create_health_router
from docmind_llmmagic.bootstrap.dependencies.health import get_health_service


def get_health_router() -> APIRouter:
    """Return the health router."""
    return create_health_router(
        health_service_dependency=get_health_service,
    )
