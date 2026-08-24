"""Dapr smoke route registration for the DocMind.ai worker service."""

from fastapi import APIRouter

from docmind_worker.api.dapr_smoke import create_dapr_smoke_router
from docmind_worker.bootstrap.dependencies.dapr_smoke import (
    build_dapr_smoke_event_consumer_dependency,
)
from docmind_worker.infrastructure.dapr_smoke.memory import InMemoryDaprSmokeEventStore


def get_dapr_smoke_router() -> APIRouter:
    """Return the local-only Dapr smoke router."""

    store = InMemoryDaprSmokeEventStore()
    return create_dapr_smoke_router(
        consumer_dependency=build_dapr_smoke_event_consumer_dependency(store=store),
    )
