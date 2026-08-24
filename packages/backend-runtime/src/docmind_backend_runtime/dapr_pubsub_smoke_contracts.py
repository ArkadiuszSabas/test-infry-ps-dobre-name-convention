"""Framework-free contracts for the local DocMind Dapr pub/sub smoke check."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import uuid4

DAPR_PUBSUB_SMOKE_PUBSUB_NAME = "docmind-redis-pubsub"
DAPR_PUBSUB_SMOKE_TOPIC = "docmind.dapr.smoke.v1"
DAPR_PUBSUB_SMOKE_ROUTE = "/dapr-smoke/pubsub"
DAPR_PUBSUB_SMOKE_SOURCE_SERVICE = "docmind-api"
DEFAULT_PUBSUB_SMOKE_MESSAGE = "Dapr local pubsub smoke test"
DEFAULT_PUBSUB_SMOKE_CORRELATION_ID = "docmind-dapr-pubsub-smoke"
DEFAULT_PUBSUB_SMOKE_API_BASE_URL = "http://127.0.0.1:5001"
DEFAULT_PUBSUB_SMOKE_WORKER_BASE_URL = "http://127.0.0.1:5003"


@dataclass(frozen=True, slots=True)
class DaprPubSubSmokeEvent:
    """Technical event payload used only by the local Dapr pub/sub smoke check."""

    operation_id: str
    correlation_id: str
    source_service: str = DAPR_PUBSUB_SMOKE_SOURCE_SERVICE
    message: str = DEFAULT_PUBSUB_SMOKE_MESSAGE

    def __post_init__(self) -> None:
        _require_non_blank("operation_id", self.operation_id)
        _require_non_blank("correlation_id", self.correlation_id)
        _require_non_blank("source_service", self.source_service)
        _require_non_blank("message", self.message)

    def to_payload(self) -> dict[str, str]:
        """Return the JSON payload published through Dapr."""

        return {
            "operation_id": self.operation_id,
            "correlation_id": self.correlation_id,
            "source_service": self.source_service,
            "message": self.message,
        }


def new_dapr_pubsub_smoke_operation_id() -> str:
    """Return a compact operation id for a local pub/sub smoke run."""

    return f"local-smoke-{uuid4().hex[:12]}"


def dapr_pubsub_smoke_event_from_mapping(
    payload: Mapping[str, object],
) -> DaprPubSubSmokeEvent:
    """Parse a smoke event from a generic JSON mapping."""

    return DaprPubSubSmokeEvent(
        operation_id=_required_str(payload, "operation_id"),
        correlation_id=_required_str(payload, "correlation_id"),
        source_service=_required_str(payload, "source_service"),
        message=_required_str(payload, "message"),
    )


def _required_str(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Dapr pub/sub smoke event field '{key}' must be a string.")

    return _require_non_blank(key, value)


def _require_non_blank(name: str, value: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{name} must not be blank.")

    return normalized_value
