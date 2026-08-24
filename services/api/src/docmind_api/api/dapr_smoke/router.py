"""HTTP endpoints for the API-owned Dapr smoke slice."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from docmind_api.api.dapr_smoke.schemas import (
    PublishDaprSmokeEventEnvelope,
    PublishDaprSmokeEventRequest,
    PublishDaprSmokeEventSchema,
)
from docmind_api.application.dapr_smoke.service import (
    PublishDaprSmokeEventCommand,
    PublishDaprSmokeEventUseCase,
)
from docmind_backend_runtime import get_correlation_id
from docmind_backend_runtime.dapr_pubsub_smoke_contracts import (
    DAPR_PUBSUB_SMOKE_ROUTE,
    DEFAULT_PUBSUB_SMOKE_CORRELATION_ID,
)

PublishDaprSmokeEventUseCaseDependency = Callable[[], PublishDaprSmokeEventUseCase]


def create_dapr_smoke_router(
    *,
    publish_use_case_dependency: PublishDaprSmokeEventUseCaseDependency,
) -> APIRouter:
    """Create local-only Dapr smoke routes for the API service."""

    router = APIRouter(tags=["dapr-smoke"])

    async def publish_smoke_event(
        request: PublishDaprSmokeEventRequest,
        response: Response,
        use_case: Annotated[
            PublishDaprSmokeEventUseCase,
            Depends(publish_use_case_dependency),
        ],
    ) -> PublishDaprSmokeEventEnvelope:
        result = await use_case.execute(
            PublishDaprSmokeEventCommand(
                operation_id=request.operation_id.strip(),
                correlation_id=get_correlation_id() or DEFAULT_PUBSUB_SMOKE_CORRELATION_ID,
                message=request.message.strip(),
            ),
        )
        response.status_code = HTTPStatus.ACCEPTED
        return PublishDaprSmokeEventEnvelope(
            data=PublishDaprSmokeEventSchema(
                operation_id=result.operation_id,
                correlation_id=result.correlation_id,
                source_service=result.source_service,
                pubsub_name=result.pubsub_name,
                topic_name=result.topic_name,
            ),
        )

    router.add_api_route(
        DAPR_PUBSUB_SMOKE_ROUTE,
        publish_smoke_event,
        methods=["POST"],
        response_model=PublishDaprSmokeEventEnvelope,
    )
    return router
