"""Application ports for the API-owned Dapr pub/sub smoke slice."""

from typing import Protocol

from docmind_backend_runtime.dapr_pubsub_smoke_contracts import DaprPubSubSmokeEvent


class DaprSmokeEventPublisher(Protocol):
    """Publishes the technical Dapr pub/sub smoke event."""

    async def publish(self, event: DaprPubSubSmokeEvent) -> None:
        """Publish the event."""
