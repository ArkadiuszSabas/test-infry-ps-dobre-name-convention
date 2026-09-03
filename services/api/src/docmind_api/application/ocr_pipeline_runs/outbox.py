"""At-least-once publication of API-owned OCR run requests."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Protocol

from docmind_api.application.ocr_pipeline_runs.ports import (
    OcrRunOutboxRecord,
    OcrRunOutboxRepository,
)


class OcrRunRequestPublisher(Protocol):
    """Publishes one event to the configured Dapr topic."""

    async def publish(
        self,
        *,
        topic: str,
        event_type: str,
        event_id: str,
        payload: Mapping[str, object],
    ) -> None: ...


class OcrRunOutboxRelay:
    """Relay pending rows and retain them when publication fails."""

    def __init__(
        self,
        *,
        repository: OcrRunOutboxRepository,
        publisher: OcrRunRequestPublisher,
    ) -> None:
        self._repository = repository
        self._publisher = publisher

    async def relay_once(self, *, limit: int = 20) -> int:
        """Publish a bounded batch; an error leaves the row pending for retry."""

        records = await self._repository.claim_request_outbox(limit=limit)
        published = 0
        for record in records:
            await self._publish(record)
            if await self._repository.mark_request_outbox_published(
                record.id,
                published_at=datetime.now(UTC),
            ):
                published += 1
        return published

    async def _publish(self, record: OcrRunOutboxRecord) -> None:
        await self._publisher.publish(
            topic=record.topic,
            event_type=record.event_type,
            event_id=str(record.id),
            payload=record.payload,
        )
