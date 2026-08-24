"""Runtime adapters for custom dictionary use cases."""

from datetime import UTC, datetime
from uuid import UUID, uuid4


class UtcClock:
    """Clock adapter returning timezone-aware UTC timestamps."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""

        return datetime.now(UTC)


class UuidDictionaryIdFactory:
    """Identifier generator for dictionaries."""

    def new_id(self) -> UUID:
        """Return a new UUID v4 identifier."""

        return uuid4()


class UuidDictionaryFieldIdFactory:
    """Identifier generator for dictionary fields."""

    def new_id(self) -> UUID:
        """Return a new UUID v4 identifier."""

        return uuid4()


class UuidDictionaryEntryIdFactory:
    """Identifier generator for dictionary entries."""

    def new_id(self) -> UUID:
        """Return a new UUID v4 identifier."""

        return uuid4()
