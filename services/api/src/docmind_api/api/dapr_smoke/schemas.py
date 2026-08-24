"""HTTP schemas for the API-owned Dapr smoke endpoints."""

from pydantic import BaseModel, Field

from docmind_backend_runtime.dapr_pubsub_smoke_contracts import DEFAULT_PUBSUB_SMOKE_MESSAGE


class PublishDaprSmokeEventRequest(BaseModel):
    """Request body for publishing one technical Dapr smoke event."""

    operation_id: str = Field(min_length=1, max_length=128)
    message: str = Field(default=DEFAULT_PUBSUB_SMOKE_MESSAGE, min_length=1, max_length=512)


class PublishDaprSmokeEventSchema(BaseModel):
    """HTTP schema returned after the smoke event was accepted."""

    operation_id: str
    correlation_id: str
    source_service: str
    pubsub_name: str
    topic_name: str


class PublishDaprSmokeEventEnvelope(BaseModel):
    """Standard API response envelope for Dapr smoke publishing."""

    data: PublishDaprSmokeEventSchema
    meta: dict[str, str] = Field(default_factory=dict)
