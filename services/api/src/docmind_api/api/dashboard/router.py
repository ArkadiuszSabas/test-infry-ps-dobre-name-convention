"""HTTP endpoint for the operational dashboard."""

from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from docmind_api.api.auth.dependencies import require_permissions
from docmind_api.api.dashboard.mappers import to_dashboard_overview_envelope
from docmind_api.api.dashboard.schemas import DashboardOverviewEnvelope
from docmind_api.application.dashboard.service import DashboardOverviewService
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission

DashboardOverviewServiceDependency = Callable[..., DashboardOverviewService]


def create_dashboard_router(
    *,
    dashboard_service_dependency: DashboardOverviewServiceDependency,
) -> APIRouter:
    """Create the read-only dashboard router."""

    router = APIRouter(prefix="/dashboard", tags=["dashboard"])
    require_documents_read = require_permissions(Permission.DOCUMENTS_READ)

    async def get_overview(
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_read)],
        service: Annotated[
            DashboardOverviewService,
            Depends(dashboard_service_dependency),
        ],
        window_days: Annotated[
            Literal["7", "30"],
            Query(description="Rolling dashboard window in calendar days."),
        ] = "7",
    ) -> DashboardOverviewEnvelope:
        return to_dashboard_overview_envelope(
            await service.get_overview(window_days=int(window_days)),
        )

    router.add_api_route(
        "/overview",
        get_overview,
        methods=["GET"],
        response_model=DashboardOverviewEnvelope,
    )
    return router
