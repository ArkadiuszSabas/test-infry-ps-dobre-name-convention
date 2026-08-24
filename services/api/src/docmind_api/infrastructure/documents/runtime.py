"""Runtime adapters for document registry use cases."""

from datetime import UTC, datetime
from uuid import UUID, uuid4


class UtcClock:
    """Clock adapter returning timezone-aware UTC timestamps."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""

        return datetime.now(UTC)


class UuidDocumentIdFactory:
    """Document ID factory backed by UUIDv4."""

    def new_id(self) -> UUID:
        """Return a new document UUID."""

        return uuid4()
