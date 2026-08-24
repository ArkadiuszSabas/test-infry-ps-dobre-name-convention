"""Use cases for the API-owned Dapr pub/sub smoke slice."""

from dataclasses import dataclass
from http import HTTPStatus

from docmind_api.application.dapr_smoke.ports import DaprSmokeEventPublisher
from docmind_backend_runtime.dapr_pubsub_smoke_contracts import (
    DAPR_PUBSUB_SMOKE_PUBSUB_NAME,
    DAPR_PUBSUB_SMOKE_SOURCE_SERVICE,
    DAPR_PUBSUB_SMOKE_TOPIC,
    DaprPubSubSmokeEvent,
)
from docmind_backend_runtime.errors import ApplicationError


@dataclass(frozen=True, slots=True)
class PublishDaprSmokeEventCommand:
    """Input for publishing one technical Dapr pub/sub smoke event."""

    operation_id: str
    correlation_id: str
    message: str


@dataclass(frozen=True, slots=True)
class PublishDaprSmokeEventResult:
    """Result returned after a smoke event was accepted for publishing."""

    operation_id: str
    correlation_id: str
    source_service: str
    pubsub_name: str
    topic_name: str


class DaprSmokePublishError(ApplicationError):
    """Raised when the API service cannot publish the smoke event through Dapr."""

    def __init__(self, *, reason: str) -> None:
        super().__init__(
            code="DAPR_SMOKE_PUBLISH_FAILED",
            message="Dapr smoke event publish failed.",
            status_code=HTTPStatus.BAD_GATEWAY,
            details={"reason": reason},
        )


class PublishDaprSmokeEventUseCase:
    """Publishes a local technical smoke event through Dapr pub/sub."""

    def __init__(self, *, publisher: DaprSmokeEventPublisher) -> None:
        self._publisher = publisher

    async def execute(self, command: PublishDaprSmokeEventCommand) -> PublishDaprSmokeEventResult:
        """Publish one smoke event."""

        event = DaprPubSubSmokeEvent(
            operation_id=command.operation_id,
            correlation_id=command.correlation_id,
            source_service=DAPR_PUBSUB_SMOKE_SOURCE_SERVICE,
            message=command.message,
        )
        await self._publisher.publish(event)

        return PublishDaprSmokeEventResult(
            operation_id=event.operation_id,
            correlation_id=event.correlation_id,
            source_service=event.source_service,
            pubsub_name=DAPR_PUBSUB_SMOKE_PUBSUB_NAME,
            topic_name=DAPR_PUBSUB_SMOKE_TOPIC,
        )
