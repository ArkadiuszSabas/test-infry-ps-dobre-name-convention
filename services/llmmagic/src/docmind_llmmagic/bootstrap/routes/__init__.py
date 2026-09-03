"""Route registration for the DocMind.ai LLM Magic service."""

from fastapi import APIRouter

from docmind_llmmagic.bootstrap.routes.health import get_health_router
from docmind_llmmagic.bootstrap.routes.internal_ocr import get_internal_ocr_router


def get_llmmagic_routers() -> tuple[APIRouter, ...]:
    """Return routers registered by the LLM Magic service."""
    return (get_health_router(), get_internal_ocr_router())
