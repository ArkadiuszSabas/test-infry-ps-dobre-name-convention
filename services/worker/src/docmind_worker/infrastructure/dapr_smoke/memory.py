"""In-memory store for local Dapr pub/sub smoke verification."""

import asyncio
from collections import OrderedDict

from docmind_backend_runtime.dapr_pubsub_smoke_contracts import DaprPubSubSmokeEvent


class InMemoryDaprSmokeEventStore:
    """Small process-local store for recently consumed smoke events."""

    def __init__(self, *, max_events: int = 100) -> None:
        self._max_events = max(max_events, 1)
        self._events: OrderedDict[str, DaprPubSubSmokeEvent] = OrderedDict()
        self._lock = asyncio.Lock()

    async def save(self, event: DaprPubSubSmokeEvent) -> None:
        """Save one consumed event."""

        async with self._lock:
            self._events[event.operation_id] = event
            self._events.move_to_end(event.operation_id)
            while len(self._events) > self._max_events:
                self._events.popitem(last=False)

    async def get(self, operation_id: str) -> DaprPubSubSmokeEvent | None:
        """Return one consumed event by operation id, if present."""

        async with self._lock:
            event = self._events.get(operation_id)
            if event is None:
                return None

            self._events.move_to_end(operation_id)
            return event
