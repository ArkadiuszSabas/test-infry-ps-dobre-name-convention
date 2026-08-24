"""Dapr-backed publisher for the API-owned smoke event."""

from docmind_api.application.dapr_smoke.service import DaprSmokePublishError
from docmind_backend_runtime.correlation import CORRELATION_ID_HEADER
from docmind_backend_runtime.dapr import DaprClientError, DaprHttpClient
from docmind_backend_runtime.dapr_pubsub_smoke_contracts import (
    DAPR_PUBSUB_SMOKE_PUBSUB_NAME,
    DAPR_PUBSUB_SMOKE_TOPIC,
    DaprPubSubSmokeEvent,
)


class DaprHttpSmokeEventPublisher:
    """Publishes the technical smoke event through the local Dapr sidecar."""

    def __init__(
        self,
        *,
        dapr_client: DaprHttpClient,
        pubsub_name: str = DAPR_PUBSUB_SMOKE_PUBSUB_NAME,
        topic_name: str = DAPR_PUBSUB_SMOKE_TOPIC,
    ) -> None:
        self._dapr_client = dapr_client
        self._pubsub_name = pubsub_name
        self._topic_name = topic_name

    async def publish(self, event: DaprPubSubSmokeEvent) -> None:
        """Publish the event through Dapr pub/sub."""

        try:
            response = await self._dapr_client.publish_event(
                self._pubsub_name,
                self._topic_name,
                headers={CORRELATION_ID_HEADER: event.correlation_id},
                json_body=event.to_payload(),
            )
        except DaprClientError as error:
            raise DaprSmokePublishError(reason=str(error)) from error

        if response.status_code < 200 or response.status_code >= 300:
            raise DaprSmokePublishError(
                reason=(
                    f"Dapr publish returned HTTP {response.status_code} for "
                    f"pubsub '{self._pubsub_name}' topic '{self._topic_name}'."
                ),
            )
