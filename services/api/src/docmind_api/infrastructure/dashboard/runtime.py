"""Runtime adapters for the dashboard."""

from datetime import UTC, datetime


class UtcDashboardClock:
    """Return timezone-aware UTC timestamps."""

    def now(self) -> datetime:
        return datetime.now(UTC)
