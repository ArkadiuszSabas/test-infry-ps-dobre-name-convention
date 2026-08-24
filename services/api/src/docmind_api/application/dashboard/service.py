"""Operational dashboard application service."""

from docmind_api.application.dashboard.models import DashboardOverview
from docmind_api.application.dashboard.ports import DashboardClock, DashboardOverviewReader

SUPPORTED_DASHBOARD_WINDOWS = frozenset({7, 30})


class DashboardOverviewService:
    """Coordinates one consistent overview snapshot."""

    def __init__(
        self,
        *,
        reader: DashboardOverviewReader,
        clock: DashboardClock,
    ) -> None:
        self._reader = reader
        self._clock = clock

    async def get_overview(self, *, window_days: int) -> DashboardOverview:
        """Return the overview for one supported rolling calendar window."""

        if window_days not in SUPPORTED_DASHBOARD_WINDOWS:
            raise ValueError("Dashboard window_days must be 7 or 30.")
        return await self._reader.get_overview(
            window_days=window_days,
            generated_at=self._clock.now(),
        )
