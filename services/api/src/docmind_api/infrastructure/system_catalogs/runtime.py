"""Runtime adapters for system catalog workflows."""

from datetime import UTC, datetime
from uuid import UUID, uuid4


class UtcClock:
    """Clock implementation using timezone-aware UTC datetimes."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidSystemCatalogIdFactory:
    """UUID identifier factory for system catalog rows."""

    def new_id(self) -> UUID:
        return uuid4()
