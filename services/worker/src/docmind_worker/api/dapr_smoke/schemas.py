"""HTTP schemas for the worker-owned Dapr smoke endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class DaprPubSubSubscriptionSchema(BaseModel):
    """Dapr subscription declaration returned by /dapr/subscribe."""

    pubsubname: str
    topic: str
    route: str


class DaprPubSubCloudEventSchema(BaseModel):
    """Minimal CloudEvent envelope delivered by Dapr pub/sub."""

    data: dict[str, Any]


class DaprPubSubAckSchema(BaseModel):
    """Acknowledgement returned to Dapr after successful event handling."""

    status: str = "SUCCESS"


class ConsumedDaprSmokeEventSchema(BaseModel):
    """HTTP schema for one consumed Dapr smoke event."""

    operation_id: str
    correlation_id: str
    source_service: str
    message: str


class ConsumedDaprSmokeEventEnvelope(BaseModel):
    """Standard response envelope for consumed Dapr smoke events."""

    data: ConsumedDaprSmokeEventSchema
    meta: dict[str, str] = Field(default_factory=dict)
