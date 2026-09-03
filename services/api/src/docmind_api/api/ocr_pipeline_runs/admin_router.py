"""Administrative cross-document OCR run routes."""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from docmind_api.api.auth.dependencies import require_permissions
from docmind_api.api.ocr_pipeline_runs.admin_mappers import (
    to_admin_detail_envelope,
    to_admin_list_envelope,
)
from docmind_api.api.ocr_pipeline_runs.admin_schemas import (
    AdminOcrRunDetailEnvelope,
    AdminOcrRunListEnvelope,
)
from docmind_api.application.ocr_pipeline_runs.admin_read_model import (
    AdminOcrRunFilters,
    AdminOcrRunReadService,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission
from docmind_api.domain.ocr_pipeline_runs.models import OcrPipelineRunStatus

AdminOcrRunReadServiceDependency = Callable[..., AdminOcrRunReadService]


def create_admin_ocr_runs_router(
    *, service_dependency: AdminOcrRunReadServiceDependency
) -> APIRouter:
    router = APIRouter(prefix="/admin/ocr/pipeline-runs", tags=["admin"])
    require_admin = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)

    async def list_runs(
        _actor: Annotated[AuthenticatedActor, Depends(require_admin)],
        service: Annotated[AdminOcrRunReadService, Depends(service_dependency)],
        view: Annotated[Literal["active", "history"], Query()] = "active",
        status: Annotated[list[OcrPipelineRunStatus] | None, Query()] = None,
        pipeline_id: Annotated[UUID | None, Query()] = None,
        document_type_id: Annotated[UUID | None, Query()] = None,
        source: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
        connector: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
        created_from: Annotated[datetime | None, Query()] = None,
        created_to: Annotated[datetime | None, Query()] = None,
        updated_before: Annotated[datetime | None, Query()] = None,
        search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> AdminOcrRunListEnvelope:
        page = await service.list_runs(
            AdminOcrRunFilters(
                view=view,
                statuses=tuple(status or ()),
                pipeline_id=pipeline_id,
                document_type_id=document_type_id,
                source=source,
                connector=connector,
                created_from=created_from,
                created_to=created_to,
                updated_before=updated_before,
                search=search,
                limit=limit,
                offset=offset,
            )
        )
        return to_admin_list_envelope(page)

    async def get_run(
        run_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin)],
        service: Annotated[AdminOcrRunReadService, Depends(service_dependency)],
    ) -> AdminOcrRunDetailEnvelope:
        return to_admin_detail_envelope(await service.get_run(run_id))

    router.add_api_route("", list_runs, methods=["GET"], response_model=AdminOcrRunListEnvelope)
    router.add_api_route(
        "/{run_id}", get_run, methods=["GET"], response_model=AdminOcrRunDetailEnvelope
    )
    return router
