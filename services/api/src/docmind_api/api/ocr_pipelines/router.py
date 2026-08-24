"""HTTP endpoints for OCR pipeline admin contracts."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from docmind_api.api.auth.dependencies import require_cookie_csrf_protection, require_permissions
from docmind_api.api.ocr_pipelines.mappers import (
    to_block_catalog_schema,
    to_pipeline_detail_schema,
    to_pipeline_summary_schema,
    to_validation_schema,
)
from docmind_api.api.ocr_pipelines.request_mapping import (
    description_update_from_request,
    name_update_from_request,
    steps_from_request,
    steps_update_from_request,
)
from docmind_api.api.ocr_pipelines.schemas import (
    CreateOcrPipelineRequest,
    DeleteOcrPipelineEnvelope,
    DeleteOcrPipelineSchema,
    OcrPipelineBlockCatalogEnvelope,
    OcrPipelineEnvelope,
    OcrPipelineListEnvelope,
    OcrPipelineListMeta,
    OcrPipelineListSchema,
    OcrPipelineValidationEnvelope,
    UpdateOcrPipelineDraftRequest,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.application.ocr_pipelines.commands import (
    ArchiveOcrPipelineCommand,
    CreateOcrPipelineCommand,
    DeleteOcrPipelineCommand,
    GetOcrPipelineQuery,
    ListOcrPipelinesQuery,
    MakeDefaultOcrPipelineCommand,
    PublishOcrPipelineCommand,
    UpdateOcrPipelineDraftCommand,
    ValidateOcrPipelineCommand,
)
from docmind_api.application.ocr_pipelines.service import OcrPipelineAdminService
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission

OcrPipelineAdminServiceDependency = Callable[..., OcrPipelineAdminService]
UserSessionServiceDependency = Callable[..., UserSessionService]


def create_ocr_pipelines_router(
    *,
    ocr_pipeline_admin_dependency: OcrPipelineAdminServiceDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create OCR pipeline admin routes."""

    router = APIRouter(prefix="/admin/ocr", tags=["ocr-pipelines"])
    require_admin_settings_manage = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def get_block_catalog(
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            OcrPipelineAdminService,
            Depends(ocr_pipeline_admin_dependency),
        ],
    ) -> OcrPipelineBlockCatalogEnvelope:
        catalog = await service.get_block_catalog()
        return OcrPipelineBlockCatalogEnvelope(data=to_block_catalog_schema(catalog))

    async def list_pipelines(
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            OcrPipelineAdminService,
            Depends(ocr_pipeline_admin_dependency),
        ],
    ) -> OcrPipelineListEnvelope:
        result = await service.list_pipelines(ListOcrPipelinesQuery())
        return OcrPipelineListEnvelope(
            data=OcrPipelineListSchema(
                pipelines=[to_pipeline_summary_schema(record) for record in result.pipelines],
            ),
            meta=OcrPipelineListMeta(total_count=len(result.pipelines)),
        )

    async def create_pipeline(
        request: CreateOcrPipelineRequest,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            OcrPipelineAdminService,
            Depends(ocr_pipeline_admin_dependency),
        ],
    ) -> OcrPipelineEnvelope:
        record = await service.create_pipeline(
            CreateOcrPipelineCommand(
                name=request.name,
                description=request.description,
                steps=steps_from_request(request.steps),
                actor_id=admin_actor.actor_id,
            ),
        )
        return OcrPipelineEnvelope(data=to_pipeline_detail_schema(record))

    async def get_pipeline(
        pipeline_id: UUID,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            OcrPipelineAdminService,
            Depends(ocr_pipeline_admin_dependency),
        ],
    ) -> OcrPipelineEnvelope:
        record = await service.get_pipeline(GetOcrPipelineQuery(pipeline_id=pipeline_id))
        return OcrPipelineEnvelope(data=to_pipeline_detail_schema(record))

    async def update_draft(
        pipeline_id: UUID,
        request: UpdateOcrPipelineDraftRequest,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            OcrPipelineAdminService,
            Depends(ocr_pipeline_admin_dependency),
        ],
    ) -> OcrPipelineEnvelope:
        record = await service.update_draft(
            UpdateOcrPipelineDraftCommand(
                pipeline_id=pipeline_id,
                name=name_update_from_request(request),
                description=description_update_from_request(request),
                steps=steps_update_from_request(request),
                actor_id=admin_actor.actor_id,
            ),
        )
        return OcrPipelineEnvelope(data=to_pipeline_detail_schema(record))

    async def validate_pipeline(
        pipeline_id: UUID,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            OcrPipelineAdminService,
            Depends(ocr_pipeline_admin_dependency),
        ],
    ) -> OcrPipelineValidationEnvelope:
        validation = await service.validate_pipeline(
            ValidateOcrPipelineCommand(pipeline_id=pipeline_id, actor_id=admin_actor.actor_id)
        )
        return OcrPipelineValidationEnvelope(data=to_validation_schema(validation))

    async def publish_pipeline(
        pipeline_id: UUID,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            OcrPipelineAdminService,
            Depends(ocr_pipeline_admin_dependency),
        ],
    ) -> OcrPipelineEnvelope:
        record = await service.publish_pipeline(
            PublishOcrPipelineCommand(pipeline_id=pipeline_id, actor_id=admin_actor.actor_id)
        )
        return OcrPipelineEnvelope(data=to_pipeline_detail_schema(record))

    async def archive_pipeline(
        pipeline_id: UUID,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            OcrPipelineAdminService,
            Depends(ocr_pipeline_admin_dependency),
        ],
    ) -> OcrPipelineEnvelope:
        record = await service.archive_pipeline(
            ArchiveOcrPipelineCommand(pipeline_id=pipeline_id, actor_id=admin_actor.actor_id)
        )
        return OcrPipelineEnvelope(data=to_pipeline_detail_schema(record))

    async def delete_pipeline(
        pipeline_id: UUID,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            OcrPipelineAdminService,
            Depends(ocr_pipeline_admin_dependency),
        ],
    ) -> DeleteOcrPipelineEnvelope:
        result = await service.delete_pipeline(
            DeleteOcrPipelineCommand(pipeline_id=pipeline_id, actor_id=admin_actor.actor_id)
        )
        return DeleteOcrPipelineEnvelope(
            data=DeleteOcrPipelineSchema(id=result.pipeline_id, deleted=result.deleted),
        )

    async def make_default_pipeline(
        pipeline_id: UUID,
        admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        service: Annotated[
            OcrPipelineAdminService,
            Depends(ocr_pipeline_admin_dependency),
        ],
    ) -> OcrPipelineEnvelope:
        record = await service.make_default_pipeline(
            MakeDefaultOcrPipelineCommand(pipeline_id=pipeline_id, actor_id=admin_actor.actor_id),
        )
        return OcrPipelineEnvelope(data=to_pipeline_detail_schema(record))

    router.add_api_route(
        "/pipeline-blocks",
        get_block_catalog,
        methods=["GET"],
        response_model=OcrPipelineBlockCatalogEnvelope,
    )
    router.add_api_route(
        "/pipelines",
        list_pipelines,
        methods=["GET"],
        response_model=OcrPipelineListEnvelope,
    )
    router.add_api_route(
        "/pipelines",
        create_pipeline,
        methods=["POST"],
        status_code=HTTPStatus.CREATED,
        response_model=OcrPipelineEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/pipelines/{pipeline_id}",
        get_pipeline,
        methods=["GET"],
        response_model=OcrPipelineEnvelope,
    )
    router.add_api_route(
        "/pipelines/{pipeline_id}/draft",
        update_draft,
        methods=["PATCH"],
        response_model=OcrPipelineEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/pipelines/{pipeline_id}/validate",
        validate_pipeline,
        methods=["POST"],
        response_model=OcrPipelineValidationEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/pipelines/{pipeline_id}/publish",
        publish_pipeline,
        methods=["POST"],
        response_model=OcrPipelineEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/pipelines/{pipeline_id}/archive",
        archive_pipeline,
        methods=["POST"],
        response_model=OcrPipelineEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/pipelines/{pipeline_id}",
        delete_pipeline,
        methods=["DELETE"],
        response_model=DeleteOcrPipelineEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/pipelines/{pipeline_id}/make-default",
        make_default_pipeline,
        methods=["POST"],
        response_model=OcrPipelineEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    return router
