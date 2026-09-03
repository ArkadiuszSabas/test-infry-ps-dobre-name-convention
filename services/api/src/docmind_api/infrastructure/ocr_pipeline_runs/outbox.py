"""Dapr publisher for the API-owned OCR run outbox."""

from collections.abc import Mapping
from datetime import UTC, datetime

from docmind_backend_runtime import DaprClientError, DaprHttpClient
from docmind_core.ocr_pipeline import OCR_RUN_REQUESTED_EVENT_TYPE


class OcrRunOutboxPublishError(RuntimeError):
    """Raised when Dapr does not accept an OCR run request."""


class DaprOcrRunRequestPublisher:
    """Publish a stable CloudEvent envelope through Dapr pub/sub."""

    def __init__(
        self,
        *,
        dapr_client: DaprHttpClient,
        pubsub_name: str,
    ) -> None:
        self._dapr_client = dapr_client
        self._pubsub_name = pubsub_name

    async def publish(
        self,
        *,
        topic: str,
        event_type: str,
        event_id: str,
        payload: Mapping[str, object],
    ) -> None:
        body = {
            "specversion": "1.0",
            "id": event_id,
            "source": "docmind-api",
            "type": (
                OCR_RUN_REQUESTED_EVENT_TYPE if event_type == "OcrRunRequestedV1" else event_type
            ),
            "time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "data": dict(payload),
        }
        try:
            response = await self._dapr_client.publish_event(
                self._pubsub_name,
                topic,
                headers={"Content-Type": "application/cloudevents+json"},
                json_body=body,
            )
        except DaprClientError as error:
            raise OcrRunOutboxPublishError("Dapr OCR outbox publication failed.") from error
        if response.status_code < 200 or response.status_code >= 300:
            raise OcrRunOutboxPublishError(
                f"Dapr OCR outbox publication returned HTTP {response.status_code}."
            )
