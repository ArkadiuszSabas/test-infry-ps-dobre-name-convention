"""Runtime adapters for document type attribute requirement use cases."""

from datetime import UTC, datetime
from uuid import UUID, uuid4


class UtcClock:
    """Clock adapter returning timezone-aware UTC timestamps."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""

        return datetime.now(UTC)


class UuidAttributeRequirementIdFactory:
    """Identifier generator backed by random UUID v4 values."""

    def new_id(self) -> UUID:
        """Return a new UUID v4 identifier."""

        return uuid4()
