"""Runtime adapters for workspace registry IDs and timestamps."""

from datetime import UTC, datetime
from uuid import UUID, uuid4


class UtcClock:
    """Clock adapter returning timezone-aware UTC timestamps."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidWorkspaceIdFactory:
    """UUID v4 factory for workspace and provisioning-request IDs."""

    def new_id(self) -> UUID:
        return uuid4()
