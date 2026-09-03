"""Dapr pub/sub endpoints for OCR run dispatch."""

from collections.abc import Callable, Mapping
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError

from docmind_backend_runtime.dapr_pubsub_smoke_contracts import (
    DAPR_PUBSUB_SMOKE_PUBSUB_NAME,
    DAPR_PUBSUB_SMOKE_ROUTE,
    DAPR_PUBSUB_SMOKE_TOPIC,
)
from docmind_core.ocr_pipeline import (
    OCR_DOCUMENT_PROCESSING_TOPIC,
    OCR_RUN_CANCELLATION_REQUESTED_EVENT_TYPE,
    OCR_RUN_REQUESTED_EVENT_TYPE,
    OCR_RUN_REQUESTED_ROUTE,
    OcrRunCancellationRequestedV1,
    OcrRunRequestedV1,
)
from docmind_worker.api.dapr_smoke.schemas import DaprPubSubAckSchema, DaprPubSubSubscriptionSchema
from docmind_worker.application.ocr_pipeline_runs.ports import (
    OcrRunCancellationRequest,
    OcrRunDispatchRequest,
)
from docmind_worker.application.ocr_pipeline_runs.service import (
    OcrRunCancellationConsumer,
    OcrRunDispatchConsumer,
    OcrRunDispatchRetryableError,
)

_WORKER_OCR_PUBSUB_NAME = "docmind-servicebus-pubsub-worker"


class _CloudEventSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    source: Literal["docmind-api"]
    specversion: Literal["1.0"]
    type: str
    data: Mapping[str, object]


OcrRunDispatchConsumerDependency = Callable[[], OcrRunDispatchConsumer]
OcrRunCancellationConsumerDependency = Callable[[], OcrRunCancellationConsumer]


def create_ocr_pipeline_run_router(
    *,
    consumer_dependency: OcrRunDispatchConsumerDependency,
    cancellation_consumer_dependency: OcrRunCancellationConsumerDependency,
    include_smoke_subscription: bool,
) -> APIRouter:
    """Create the Dapr subscription and delivery handler for whole OCR runs."""

    router = APIRouter(tags=["ocr-pipeline-runs"])

    async def get_subscriptions() -> list[DaprPubSubSubscriptionSchema]:
        subscriptions = [
            DaprPubSubSubscriptionSchema(
                pubsubname=_WORKER_OCR_PUBSUB_NAME,
                topic=OCR_DOCUMENT_PROCESSING_TOPIC,
                route=OCR_RUN_REQUESTED_ROUTE.lstrip("/"),
            ),
        ]
        if include_smoke_subscription:
            subscriptions.append(
                DaprPubSubSubscriptionSchema(
                    pubsubname=DAPR_PUBSUB_SMOKE_PUBSUB_NAME,
                    topic=DAPR_PUBSUB_SMOKE_TOPIC,
                    route=DAPR_PUBSUB_SMOKE_ROUTE.lstrip("/"),
                )
            )
        return subscriptions

    async def consume_ocr_run(
        consumer: Annotated[OcrRunDispatchConsumer, Depends(consumer_dependency)],
        cancellation_consumer: Annotated[
            OcrRunCancellationConsumer, Depends(cancellation_consumer_dependency)
        ],
        cloud_event: Annotated[dict[str, object], Body()],
    ) -> DaprPubSubAckSchema:
        try:
            validated_cloud_event = _CloudEventSchema.model_validate(cloud_event)
            if validated_cloud_event.type == OCR_RUN_CANCELLATION_REQUESTED_EVENT_TYPE:
                event = OcrRunCancellationRequestedV1.model_validate(validated_cloud_event.data)
                await cancellation_consumer.consume(
                    OcrRunCancellationRequest(
                        run_id=event.run_id,
                        document_id=event.document_id,
                        pipeline_id=event.pipeline_id,
                        attempt_id=event.attempt_id,
                        fencing_token=event.fencing_token,
                        next_event_sequence=event.next_event_sequence,
                        correlation_id=event.correlation_id,
                    )
                )
            elif validated_cloud_event.type == OCR_RUN_REQUESTED_EVENT_TYPE:
                event = OcrRunRequestedV1.model_validate(validated_cloud_event.data)
                await consumer.consume(OcrRunDispatchRequest(run_id=event.run_id))
            else:
                raise ValueError("Unsupported OCR run event type.")
        except (OcrRunDispatchRetryableError, ValidationError, ValueError) as error:
            raise HTTPException(
                status_code=500,
                detail="OCR run event delivery must be retried.",
            ) from error
        return DaprPubSubAckSchema()

    router.add_api_route(
        "/dapr/subscribe",
        get_subscriptions,
        methods=["GET"],
        response_model=list[DaprPubSubSubscriptionSchema],
    )
    router.add_api_route(
        OCR_RUN_REQUESTED_ROUTE,
        consume_ocr_run,
        methods=["POST"],
        response_model=DaprPubSubAckSchema,
    )
    return router
