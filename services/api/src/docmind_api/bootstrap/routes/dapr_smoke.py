"""Dapr smoke route registration for the DocMind.ai API service."""

from fastapi import APIRouter

from docmind_api.api.dapr_smoke import create_dapr_smoke_router
from docmind_api.bootstrap.dependencies.dapr_smoke import get_publish_dapr_smoke_event_use_case


def get_dapr_smoke_router() -> APIRouter:
    """Return the local-only Dapr smoke router."""

    return create_dapr_smoke_router(
        publish_use_case_dependency=get_publish_dapr_smoke_event_use_case,
    )
