"""HTTP endpoints for OCR pipeline run contracts."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Literal, Protocol
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict

from docmind_api.api.auth.dependencies import require_cookie_csrf_protection, require_permissions
from docmind_api.api.ocr_pipeline_runs.admin_router import (
    AdminOcrRunReadServiceDependency,
    create_admin_ocr_runs_router,
)
from docmind_api.api.ocr_pipeline_runs.mappers import (
    to_published_pipeline_option_schema,
    to_result_schema,
    to_run_list_envelope,
    to_run_schema,
)
from docmind_api.api.ocr_pipeline_runs.schemas import (
    OcrPipelineRunCompletionSchema,
    OcrPipelineRunEnvelope,
    OcrPipelineRunListEnvelope,
    OcrPipelineRunResultEnvelope,
    PublishedOcrPipelineOptionListEnvelope,
    PublishedOcrPipelineOptionListMeta,
    PublishedOcrPipelineOptionListSchema,
    StartOcrPipelineRunRequest,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.application.ocr_pipeline_runs.commands import (
    GetOcrPipelineRunQuery,
    ListDocumentOcrPipelineRunsQuery,
    StartOcrPipelineRunCommand,
)
from docmind_api.application.ocr_pipeline_runs.ports import (
    OcrEventCompletion,
    OcrEventControlRepository,
    OcrEventRunCompleter,
)
from docmind_api.application.ocr_pipeline_runs.service import OcrPipelineRunService
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission
from docmind_api.domain.ocr_pipeline_runs.models import (
    OCR_PIPELINE_RUN_LIST_DEFAULT_LIMIT,
    OCR_PIPELINE_RUN_LIST_MAX_LIMIT,
    OcrPipelineRunActorType,
    OcrPipelineRunDiagnostic,
    OcrPipelineRunError,
    OcrPipelineRunRecord,
    OcrPipelineRunStep,
)
from docmind_core.ocr_pipeline.contracts import DispatchFailedV1, OcrPipelineEventV1


class OcrPipelineRunStarter(Protocol):
    """Creates a pending OCR pipeline run before background dispatch starts."""

    async def start_run(self, command: StartOcrPipelineRunCommand) -> OcrPipelineRunRecord: ...


class OcrPipelineRunControlSettings(Protocol):
    """Configuration shape required by OCR control-plane routes."""

    @property
    def max_concurrency(self) -> int: ...

    @property
    def reservation_timeout_seconds(self) -> float: ...

    @property
    def execution_timeout_seconds(self) -> float: ...

    @property
    def defer_seconds(self) -> float: ...

    @property
    def cancellation_timeout_seconds(self) -> float: ...


OcrPipelineRunStarterDependency = Callable[..., OcrPipelineRunStarter]
OcrPipelineRunServiceDependency = Callable[..., OcrPipelineRunService]
OcrPipelineRunRepositoryDependency = Callable[..., OcrEventControlRepository]
OcrEventRunCompleterDependency = Callable[..., OcrEventRunCompleter]
OcrPipelineRunSettingsDependency = Callable[..., OcrPipelineRunControlSettings]
UserSessionServiceDependency = Callable[..., UserSessionService]

_OCR_RESULTS_PUBSUB_NAME = "docmind-servicebus-pubsub-api"
_OCR_RESULTS_TOPIC = "processing-results"


class _OcrPipelineCloudEvent(BaseModel):
    """Dapr CloudEvent envelope for one validated OCR pipeline event."""

    model_config = ConfigDict(extra="ignore")

    data: OcrPipelineEventV1


class _DispatchDeferredSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fencing_token: int


class _CancellationCallbackSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fencing_token: int


class _CancelDispatchFailedSchema(_CancellationCallbackSchema):
    code: Literal["OCR_PIPELINE_RUN_CANCELLATION_REJECTED"]


def create_ocr_pipeline_runs_router(
    *,
    ocr_pipeline_run_starter_dependency: OcrPipelineRunStarterDependency,
    ocr_pipeline_run_service_dependency: OcrPipelineRunServiceDependency,
    ocr_pipeline_run_repository_dependency: OcrPipelineRunRepositoryDependency,
    ocr_event_run_completer_dependency: OcrEventRunCompleterDependency,
    ocr_pipeline_run_settings_dependency: OcrPipelineRunSettingsDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    admin_ocr_run_read_service_dependency: AdminOcrRunReadServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create OCR pipeline run routes."""

    router = APIRouter(tags=["ocr-pipeline-runs"])
    router.include_router(
        create_admin_ocr_runs_router(service_dependency=admin_ocr_run_read_service_dependency)
    )
    require_documents_create = require_permissions(Permission.DOCUMENTS_CREATE)
    require_documents_read = require_permissions(Permission.DOCUMENTS_READ)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def start_document_run(
        document_id: UUID,
        actor: Annotated[AuthenticatedActor, Depends(require_documents_create)],
        starter: Annotated[
            OcrPipelineRunStarter,
            Depends(ocr_pipeline_run_starter_dependency),
        ],
        request: StartOcrPipelineRunRequest | None = None,
    ) -> OcrPipelineRunEnvelope:
        record = await starter.start_run(
            StartOcrPipelineRunCommand(
                document_id=document_id,
                pipeline_id=request.pipeline_id if request is not None else None,
                actor_id=actor.actor_id,
                actor_type=OcrPipelineRunActorType.HUMAN,
                actor_login=actor.email,
            ),
        )
        return OcrPipelineRunEnvelope(data=to_run_schema(record))

    async def list_published_pipelines(
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_create)],
        service: Annotated[
            OcrPipelineRunService,
            Depends(ocr_pipeline_run_service_dependency),
        ],
    ) -> PublishedOcrPipelineOptionListEnvelope:
        pipelines = await service.list_published_pipelines()
        return PublishedOcrPipelineOptionListEnvelope(
            data=PublishedOcrPipelineOptionListSchema(
                pipelines=[to_published_pipeline_option_schema(item) for item in pipelines],
            ),
            meta=PublishedOcrPipelineOptionListMeta(total_count=len(pipelines)),
        )

    async def list_document_runs(
        document_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_read)],
        service: Annotated[
            OcrPipelineRunService,
            Depends(ocr_pipeline_run_service_dependency),
        ],
        limit: Annotated[
            int,
            Query(
                description="Maximum number of OCR pipeline runs to return.",
                ge=1,
                le=OCR_PIPELINE_RUN_LIST_MAX_LIMIT,
            ),
        ] = OCR_PIPELINE_RUN_LIST_DEFAULT_LIMIT,
        offset: Annotated[
            int,
            Query(
                description="Zero-based number of matching OCR pipeline runs to skip.",
                ge=0,
            ),
        ] = 0,
    ) -> OcrPipelineRunListEnvelope:
        page = await service.list_document_runs(
            ListDocumentOcrPipelineRunsQuery(
                document_id=document_id,
                limit=limit,
                offset=offset,
            ),
        )
        return to_run_list_envelope(page)

    async def get_run_status(
        run_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_read)],
        service: Annotated[
            OcrPipelineRunService,
            Depends(ocr_pipeline_run_service_dependency),
        ],
    ) -> OcrPipelineRunEnvelope:
        record = await service.get_run(GetOcrPipelineRunQuery(run_id=run_id))
        return OcrPipelineRunEnvelope(data=to_run_schema(record))

    async def get_run_result(
        run_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_read)],
        service: Annotated[
            OcrPipelineRunService,
            Depends(ocr_pipeline_run_service_dependency),
        ],
    ) -> OcrPipelineRunResultEnvelope:
        record = await service.get_run(GetOcrPipelineRunQuery(run_id=run_id))
        return OcrPipelineRunResultEnvelope(data=to_result_schema(record))

    async def dispatch_event_run(
        run_id: UUID,
        repository: Annotated[
            OcrEventControlRepository,
            Depends(ocr_pipeline_run_repository_dependency),
        ],
        settings: Annotated[
            OcrPipelineRunControlSettings,
            Depends(ocr_pipeline_run_settings_dependency),
        ],
    ) -> dict[str, object]:
        result = await repository.dispatch_event_run(
            run_id,
            attempt_id=uuid4(),
            owner_token=uuid4(),
            max_concurrency=settings.max_concurrency,
            reservation_timeout_seconds=settings.reservation_timeout_seconds,
            execution_timeout_seconds=settings.execution_timeout_seconds,
            defer_seconds=settings.defer_seconds,
        )
        if result is None:
            return {"disposition": "deleted"}
        return {
            "disposition": result.disposition,
            "attempt_id": str(result.attempt_id) if result.attempt_id else None,
            "attempt_number": result.attempt_number,
            "fencing_token": result.fencing_token,
            "execution_deadline_at": result.execution_deadline_at,
            "run_request": result.run_request,
        }

    async def dispatch_failed(
        run_id: UUID,
        attempt_id: UUID,
        body: DispatchFailedV1,
        repository: Annotated[
            OcrEventControlRepository,
            Depends(ocr_pipeline_run_repository_dependency),
        ],
    ) -> Response:
        await repository.fail_event_dispatch(
            run_id,
            attempt_id,
            fencing_token=body.fencing_token,
            error_code=body.code.value,
        )
        return Response(status_code=204)

    async def dispatch_deferred(
        run_id: UUID,
        attempt_id: UUID,
        body: _DispatchDeferredSchema,
        repository: Annotated[
            OcrEventControlRepository,
            Depends(ocr_pipeline_run_repository_dependency),
        ],
        settings: Annotated[
            OcrPipelineRunControlSettings,
            Depends(ocr_pipeline_run_settings_dependency),
        ],
    ) -> Response:
        await repository.defer_event_dispatch(
            run_id,
            attempt_id,
            fencing_token=body.fencing_token,
            defer_seconds=settings.defer_seconds,
        )
        return Response(status_code=204)

    async def cancel_run(
        run_id: UUID,
        actor: Annotated[AuthenticatedActor, Depends(require_documents_create)],
        repository: Annotated[
            OcrEventControlRepository,
            Depends(ocr_pipeline_run_repository_dependency),
        ],
        settings: Annotated[
            OcrPipelineRunControlSettings,
            Depends(ocr_pipeline_run_settings_dependency),
        ],
    ) -> OcrPipelineRunEnvelope:
        result = await repository.request_cancellation(
            run_id,
            actor_id=actor.actor_id,
            actor_login=actor.email,
            cancellation_timeout_seconds=settings.cancellation_timeout_seconds,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="OCR pipeline run was not found.")
        return OcrPipelineRunEnvelope(data=to_run_schema(result.record))

    async def cancellation_completed(
        run_id: UUID,
        attempt_id: UUID,
        body: _CancellationCallbackSchema,
        repository: Annotated[
            OcrEventControlRepository,
            Depends(ocr_pipeline_run_repository_dependency),
        ],
    ) -> Response:
        outcome = await repository.complete_cancellation(
            run_id, attempt_id, fencing_token=body.fencing_token
        )
        return Response(status_code=409 if outcome == "stale" else 204)

    async def cancellation_dispatch_failed(
        run_id: UUID,
        attempt_id: UUID,
        body: _CancelDispatchFailedSchema,
        repository: Annotated[
            OcrEventControlRepository,
            Depends(ocr_pipeline_run_repository_dependency),
        ],
    ) -> Response:
        await repository.record_cancellation_dispatch_failure(
            run_id,
            attempt_id,
            fencing_token=body.fencing_token,
            error_code=body.code,
        )
        return Response(status_code=204)

    async def receive_pipeline_event(
        cloud_event: _OcrPipelineCloudEvent,
        repository: Annotated[
            OcrEventControlRepository,
            Depends(ocr_pipeline_run_repository_dependency),
        ],
    ) -> Response:
        await repository.apply_pipeline_event(cloud_event.data)
        return Response(status_code=204)

    async def dapr_subscriptions() -> list[dict[str, str]]:
        return [
            {
                "pubsubname": _OCR_RESULTS_PUBSUB_NAME,
                "topic": _OCR_RESULTS_TOPIC,
                "route": "/internal/events/ocr-pipeline-event",
            }
        ]

    async def complete_event_run(
        run_id: UUID,
        attempt_id: UUID,
        body: OcrPipelineRunCompletionSchema,
        completer: Annotated[
            OcrEventRunCompleter,
            Depends(ocr_event_run_completer_dependency),
        ],
    ) -> Response:
        outcome = await completer.complete(
            run_id,
            attempt_id,
            OcrEventCompletion(
                document_id=body.document_id,
                fencing_token=body.fencing_token,
                status=body.status,
                steps=tuple(
                    OcrPipelineRunStep(
                        step_id=step.step_id,
                        step_type=step.step_type,
                        implementation_id=step.implementation_id,
                        display_name=step.display_name,
                        status=step.status,
                        duration_seconds=step.duration_seconds,
                        metrics=step.metrics,
                        error=(
                            OcrPipelineRunError(code=step.error.code, message=step.error.message)
                            if step.error is not None
                            else None
                        ),
                    )
                    for step in body.steps
                ),
                metrics=body.metrics,
                diagnostics=tuple(
                    OcrPipelineRunDiagnostic(
                        severity=diagnostic.severity,
                        code=diagnostic.code,
                        message=diagnostic.message,
                        step_id=diagnostic.step_id,
                        path=diagnostic.path,
                    )
                    for diagnostic in body.diagnostics
                ),
                error=(
                    OcrPipelineRunError(code=body.error.code, message=body.error.message)
                    if body.error is not None
                    else None
                ),
                result_payload=(body.result.model_dump(mode="json") if body.result else None),
            ),
        )
        if outcome in {"stale", "expired"}:
            return Response(status_code=409)
        return Response(status_code=204)

    router.add_api_route(
        "/dapr/subscribe",
        dapr_subscriptions,
        methods=["GET"],
        response_model=list[dict[str, str]],
    )
    router.add_api_route(
        "/internal/ocr/pipeline-runs/{run_id}/dispatch",
        dispatch_event_run,
        methods=["POST"],
        response_model=dict[str, object],
        status_code=200,
    )
    router.add_api_route(
        "/internal/ocr/pipeline-runs/{run_id}/attempts/{attempt_id}/dispatch-failed",
        dispatch_failed,
        methods=["POST"],
        status_code=204,
    )
    router.add_api_route(
        "/internal/ocr/pipeline-runs/{run_id}/attempts/{attempt_id}/dispatch-deferred",
        dispatch_deferred,
        methods=["POST"],
        status_code=204,
    )
    router.add_api_route(
        "/internal/ocr/pipeline-runs/{run_id}/attempts/{attempt_id}/cancelled",
        cancellation_completed,
        methods=["POST"],
        status_code=204,
    )
    router.add_api_route(
        "/internal/ocr/pipeline-runs/{run_id}/attempts/{attempt_id}/cancel-dispatch-failed",
        cancellation_dispatch_failed,
        methods=["POST"],
        status_code=204,
    )
    router.add_api_route(
        "/internal/events/ocr-pipeline-event",
        receive_pipeline_event,
        methods=["POST"],
        status_code=204,
    )
    router.add_api_route(
        "/internal/ocr/pipeline-runs/{run_id}/attempts/{attempt_id}/complete",
        complete_event_run,
        methods=["POST"],
        status_code=204,
    )

    router.add_api_route(
        "/ocr/pipelines",
        list_published_pipelines,
        methods=["GET"],
        response_model=PublishedOcrPipelineOptionListEnvelope,
    )
    router.add_api_route(
        "/documents/{document_id}/ocr/pipeline-runs",
        start_document_run,
        methods=["POST"],
        status_code=HTTPStatus.ACCEPTED,
        response_model=OcrPipelineRunEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/documents/{document_id}/ocr/pipeline-runs",
        list_document_runs,
        methods=["GET"],
        response_model=OcrPipelineRunListEnvelope,
    )
    router.add_api_route(
        "/ocr/pipeline-runs/{run_id}",
        get_run_status,
        methods=["GET"],
        response_model=OcrPipelineRunEnvelope,
    )
    router.add_api_route(
        "/ocr/pipeline-runs/{run_id}/cancel",
        cancel_run,
        methods=["POST"],
        response_model=OcrPipelineRunEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/ocr/pipeline-runs/{run_id}/result",
        get_run_result,
        methods=["GET"],
        response_model=OcrPipelineRunResultEnvelope,
    )
    return router
