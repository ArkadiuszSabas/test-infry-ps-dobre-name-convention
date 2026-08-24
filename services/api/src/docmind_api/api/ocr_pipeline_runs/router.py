"""HTTP endpoints for OCR pipeline run contracts."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from docmind_api.api.auth.dependencies import require_cookie_csrf_protection, require_permissions
from docmind_api.api.ocr_pipeline_runs.mappers import (
    to_result_schema,
    to_run_list_envelope,
    to_run_schema,
)
from docmind_api.api.ocr_pipeline_runs.schemas import (
    OcrPipelineRunEnvelope,
    OcrPipelineRunListEnvelope,
    OcrPipelineRunResultEnvelope,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.application.ocr_pipeline_runs.commands import (
    GetOcrPipelineRunQuery,
    ListDocumentOcrPipelineRunsQuery,
    StartOcrPipelineRunCommand,
)
from docmind_api.application.ocr_pipeline_runs.ports import (
    OcrPipelineRunDispatcher,
    OcrPipelineRunScheduler,
)
from docmind_api.application.ocr_pipeline_runs.service import OcrPipelineRunService
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission
from docmind_api.domain.ocr_pipeline_runs.models import (
    OCR_PIPELINE_RUN_LIST_DEFAULT_LIMIT,
    OCR_PIPELINE_RUN_LIST_MAX_LIMIT,
    OcrPipelineRunActorType,
    OcrPipelineRunRecord,
)


class OcrPipelineRunStarter(Protocol):
    """Creates a pending OCR pipeline run before background dispatch starts."""

    async def start_run(self, command: StartOcrPipelineRunCommand) -> OcrPipelineRunRecord: ...


OcrPipelineRunStarterDependency = Callable[..., OcrPipelineRunStarter]
OcrPipelineRunServiceDependency = Callable[..., OcrPipelineRunService]
OcrPipelineRunDispatcherDependency = Callable[..., OcrPipelineRunDispatcher]
OcrPipelineRunSchedulerDependency = Callable[..., OcrPipelineRunScheduler]
UserSessionServiceDependency = Callable[..., UserSessionService]


def create_ocr_pipeline_runs_router(
    *,
    ocr_pipeline_run_starter_dependency: OcrPipelineRunStarterDependency,
    ocr_pipeline_run_service_dependency: OcrPipelineRunServiceDependency,
    ocr_pipeline_run_dispatcher_dependency: OcrPipelineRunDispatcherDependency,
    ocr_pipeline_run_scheduler_dependency: OcrPipelineRunSchedulerDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create OCR pipeline run routes."""

    router = APIRouter(tags=["ocr-pipeline-runs"])
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
        dispatcher: Annotated[
            OcrPipelineRunDispatcher,
            Depends(ocr_pipeline_run_dispatcher_dependency),
        ],
        scheduler: Annotated[
            OcrPipelineRunScheduler,
            Depends(ocr_pipeline_run_scheduler_dependency),
        ],
    ) -> OcrPipelineRunEnvelope:
        record = await starter.start_run(
            StartOcrPipelineRunCommand(
                document_id=document_id,
                actor_id=actor.actor_id,
                actor_type=OcrPipelineRunActorType.HUMAN,
                actor_login=actor.email,
            ),
        )
        scheduler.schedule(dispatcher.dispatch, record.id)
        return OcrPipelineRunEnvelope(data=to_run_schema(record))

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
        "/ocr/pipeline-runs/{run_id}/result",
        get_run_result,
        methods=["GET"],
        response_model=OcrPipelineRunResultEnvelope,
    )
    return router
