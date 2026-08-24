"""Dashboard route registration."""

from fastapi import APIRouter

from docmind_api.api.dashboard.router import create_dashboard_router
from docmind_api.bootstrap.dependencies.dashboard import get_dashboard_overview_service


def get_dashboard_router() -> APIRouter:
    """Return the operational dashboard router."""

    return create_dashboard_router(
        dashboard_service_dependency=get_dashboard_overview_service,
    )
