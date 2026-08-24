"""Capability registry route registration."""

from fastapi import APIRouter

from docmind_api.api.capabilities import create_capabilities_router
from docmind_api.bootstrap.dependencies.connectors import get_capability_registry_service


def get_capabilities_router() -> APIRouter:
    """Return the capability registry router."""

    return create_capabilities_router(
        capability_registry_dependency=get_capability_registry_service,
    )
