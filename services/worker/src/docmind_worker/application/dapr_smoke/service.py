"""Use cases for the worker-owned Dapr pub/sub smoke slice."""

from dataclasses import dataclass

from docmind_backend_runtime.dapr_pubsub_smoke_contracts import DaprPubSubSmokeEvent
from docmind_backend_runtime.errors import NotFoundError
from docmind_worker.application.dapr_smoke.ports import DaprSmokeEventStore


@dataclass(frozen=True, slots=True)
class ConsumedDaprSmokeEventResult:
    """Result returned for a consumed smoke event."""

    operation_id: str
    correlation_id: str
    source_service: str
    message: str


class DaprSmokeEventConsumer:
    """Consumes and exposes local technical Dapr smoke events."""

    def __init__(self, *, store: DaprSmokeEventStore) -> None:
        self._store = store

    async def consume(self, event: DaprPubSubSmokeEvent) -> ConsumedDaprSmokeEventResult:
        """Record one event delivered by Dapr pub/sub."""

        await self._store.save(event)
        return _to_result(event)

    async def get_consumed_event(self, operation_id: str) -> ConsumedDaprSmokeEventResult:
        """Return a consumed smoke event or raise a standard not-found error."""

        event = await self._store.get(operation_id.strip())
        if event is None:
            raise NotFoundError(
                code="DAPR_SMOKE_EVENT_NOT_FOUND",
                message="Dapr smoke event was not consumed by the worker.",
                details={"operation_id": operation_id},
            )

        return _to_result(event)


def _to_result(event: DaprPubSubSmokeEvent) -> ConsumedDaprSmokeEventResult:
    return ConsumedDaprSmokeEventResult(
        operation_id=event.operation_id,
        correlation_id=event.correlation_id,
        source_service=event.source_service,
        message=event.message,
    )
