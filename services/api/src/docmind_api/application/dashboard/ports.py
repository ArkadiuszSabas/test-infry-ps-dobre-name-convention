"""Application ports for dashboard overview reads."""

from datetime import datetime
from typing import Protocol

from docmind_api.application.dashboard.models import DashboardOverview


class DashboardClock(Protocol):
    """Clock used to keep one overview snapshot internally consistent."""

    def now(self) -> datetime: ...


class DashboardOverviewReader(Protocol):
    """Reads one database-aggregated dashboard snapshot."""

    async def get_overview(
        self,
        *,
        window_days: int,
        generated_at: datetime,
    ) -> DashboardOverview: ...
