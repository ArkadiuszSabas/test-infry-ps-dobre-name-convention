"""Application ports for the worker-owned Dapr pub/sub smoke slice."""

from typing import Protocol

from docmind_backend_runtime.dapr_pubsub_smoke_contracts import DaprPubSubSmokeEvent


class DaprSmokeEventStore(Protocol):
    """Stores consumed technical Dapr smoke events for local verification."""

    async def save(self, event: DaprPubSubSmokeEvent) -> None:
        """Save one consumed event."""

    async def get(self, operation_id: str) -> DaprPubSubSmokeEvent | None:
        """Return one consumed event by operation id, if present."""
