"""HTTP endpoints for the worker-owned Dapr smoke slice."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from docmind_backend_runtime.dapr_pubsub_smoke_contracts import (
    DAPR_PUBSUB_SMOKE_ROUTE,
    dapr_pubsub_smoke_event_from_mapping,
)
from docmind_backend_runtime.errors import ValidationApplicationError
from docmind_worker.api.dapr_smoke.schemas import (
    ConsumedDaprSmokeEventEnvelope,
    ConsumedDaprSmokeEventSchema,
    DaprPubSubAckSchema,
    DaprPubSubCloudEventSchema,
)
from docmind_worker.application.dapr_smoke.service import DaprSmokeEventConsumer

DaprSmokeEventConsumerDependency = Callable[[], DaprSmokeEventConsumer]


def create_dapr_smoke_router(
    *,
    consumer_dependency: DaprSmokeEventConsumerDependency,
) -> APIRouter:
    """Create local-only Dapr smoke routes for the worker service."""

    router = APIRouter(tags=["dapr-smoke"])

    async def consume_smoke_event(
        cloud_event: DaprPubSubCloudEventSchema,
        consumer: Annotated[DaprSmokeEventConsumer, Depends(consumer_dependency)],
    ) -> DaprPubSubAckSchema:
        try:
            event = dapr_pubsub_smoke_event_from_mapping(cloud_event.data)
        except ValueError as error:
            raise ValidationApplicationError(
                code="DAPR_SMOKE_EVENT_INVALID",
                message="Dapr smoke event payload is invalid.",
                details={"reason": str(error)},
            ) from error

        await consumer.consume(event)
        return DaprPubSubAckSchema()

    async def get_consumed_event(
        operation_id: str,
        consumer: Annotated[DaprSmokeEventConsumer, Depends(consumer_dependency)],
    ) -> ConsumedDaprSmokeEventEnvelope:
        event = await consumer.get_consumed_event(operation_id)
        return ConsumedDaprSmokeEventEnvelope(
            data=ConsumedDaprSmokeEventSchema(
                operation_id=event.operation_id,
                correlation_id=event.correlation_id,
                source_service=event.source_service,
                message=event.message,
            ),
        )

    router.add_api_route(
        DAPR_PUBSUB_SMOKE_ROUTE,
        consume_smoke_event,
        methods=["POST"],
        response_model=DaprPubSubAckSchema,
    )
    router.add_api_route(
        f"{DAPR_PUBSUB_SMOKE_ROUTE}/{{operation_id}}",
        get_consumed_event,
        methods=["GET"],
        response_model=ConsumedDaprSmokeEventEnvelope,
    )
    return router
