"""Dashboard dependency factories."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.dashboard.service import DashboardOverviewService
from docmind_api.bootstrap.dependencies.database import get_database_session
from docmind_api.infrastructure.dashboard.runtime import UtcDashboardClock
from docmind_api.infrastructure.persistence.dashboard.repositories import (
    SqlAlchemyDashboardOverviewReader,
)


def get_dashboard_overview_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DashboardOverviewService:
    """Return the request-scoped dashboard overview service."""

    return DashboardOverviewService(
        reader=SqlAlchemyDashboardOverviewReader(session),
        clock=UtcDashboardClock(),
    )
