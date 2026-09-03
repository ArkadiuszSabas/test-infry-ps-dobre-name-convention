"""Runtime adapters for OCR pipeline runs."""

from datetime import UTC, datetime
from uuid import UUID, uuid4


class UtcClock:
    """UTC clock used for OCR pipeline run timestamps."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""

        return datetime.now(tz=UTC)


class UuidOcrPipelineRunIdFactory:
    """UUID4 id factory for OCR pipeline runs."""

    def new_id(self) -> UUID:
        """Return a new OCR pipeline run id."""

        return uuid4()
