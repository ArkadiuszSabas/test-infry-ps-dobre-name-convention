"""HTTP attribute category catalog endpoints for the DocMind.ai API service."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from docmind_api.api.attributes.schemas import (
    AttributeCategoryEnvelope,
    AttributeCategoryListEnvelope,
    AttributeCategoryListMeta,
    AttributeCategoryListSchema,
    AttributeCategorySchema,
    CreateAttributeCategoryRequest,
    DeleteAttributeCategoryEnvelope,
    DeleteAttributeCategorySchema,
    UpdateAttributeCategoryRequest,
)
from docmind_api.api.auth.dependencies import (
    require_cookie_csrf_protection,
    require_permissions,
)
from docmind_api.application.attributes.category_service import (
    PRESERVE_ATTRIBUTE_CATEGORY_FIELD,
    AttributeCategoryCatalogService,
    AttributeCategoryFlagsUpdate,
    AttributeCategoryLabelUpdate,
    AttributeCategoryListStatus,
    CreateAttributeCategoryCommand,
    DeactivateAttributeCategoryCommand,
    DeleteAttributeCategoryCommand,
    UpdateAttributeCategoryCommand,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.domain.attributes.models import AttributeCategory
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission

AttributeCategoryCatalogServiceDependency = Callable[..., AttributeCategoryCatalogService]
UserSessionServiceDependency = Callable[..., UserSessionService]


def create_attribute_categories_router(
    *,
    attribute_category_catalog_dependency: AttributeCategoryCatalogServiceDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create the system attribute category catalog router."""

    router = APIRouter(prefix="/attributes/categories", tags=["attributes"])
    require_admin_settings_manage = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def create_attribute_category(
        request: CreateAttributeCategoryRequest,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            AttributeCategoryCatalogService,
            Depends(attribute_category_catalog_dependency),
        ],
    ) -> AttributeCategoryEnvelope:
        category = await catalog.create_attribute_category(
            CreateAttributeCategoryCommand(
                external_id=request.external_id,
                label=request.label,
                flags=request.flags,
            ),
        )
        return AttributeCategoryEnvelope(data=_to_attribute_category_schema(category))

    async def list_attribute_categories(
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            AttributeCategoryCatalogService,
            Depends(attribute_category_catalog_dependency),
        ],
        status: Annotated[
            AttributeCategoryListStatus,
            Query(description="Filter attribute categories by lifecycle status."),
        ] = AttributeCategoryListStatus.ACTIVE,
    ) -> AttributeCategoryListEnvelope:
        result = await catalog.list_attribute_categories(status=status)
        return AttributeCategoryListEnvelope(
            data=AttributeCategoryListSchema(
                categories=[
                    _to_attribute_category_schema(category) for category in result.categories
                ],
            ),
            meta=AttributeCategoryListMeta(
                total_count=result.total_count,
                active_count=result.active_count,
                inactive_count=result.inactive_count,
                returned_count=result.returned_count,
                status=result.status,
            ),
        )

    async def update_attribute_category(
        category_id: UUID,
        request: UpdateAttributeCategoryRequest,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            AttributeCategoryCatalogService,
            Depends(attribute_category_catalog_dependency),
        ],
    ) -> AttributeCategoryEnvelope:
        category = await catalog.update_attribute_category(
            UpdateAttributeCategoryCommand(
                category_id=category_id,
                label=_category_label_update_from_request(request),
                flags=_category_flags_update_from_request(request),
            ),
        )
        return AttributeCategoryEnvelope(data=_to_attribute_category_schema(category))

    async def deactivate_attribute_category(
        category_id: UUID,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            AttributeCategoryCatalogService,
            Depends(attribute_category_catalog_dependency),
        ],
    ) -> AttributeCategoryEnvelope:
        category = await catalog.deactivate_attribute_category(
            DeactivateAttributeCategoryCommand(category_id=category_id),
        )
        return AttributeCategoryEnvelope(data=_to_attribute_category_schema(category))

    async def delete_attribute_category(
        category_id: UUID,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            AttributeCategoryCatalogService,
            Depends(attribute_category_catalog_dependency),
        ],
    ) -> DeleteAttributeCategoryEnvelope:
        result = await catalog.delete_attribute_category(
            DeleteAttributeCategoryCommand(category_id=category_id),
        )
        return DeleteAttributeCategoryEnvelope(
            data=DeleteAttributeCategorySchema(id=result.category_id, deleted=result.deleted),
        )

    router.add_api_route(
        "",
        create_attribute_category,
        methods=["POST"],
        status_code=HTTPStatus.CREATED,
        response_model=AttributeCategoryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "",
        list_attribute_categories,
        methods=["GET"],
        response_model=AttributeCategoryListEnvelope,
    )
    router.add_api_route(
        "/{category_id}",
        update_attribute_category,
        methods=["PATCH"],
        response_model=AttributeCategoryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{category_id}/deactivate",
        deactivate_attribute_category,
        methods=["POST"],
        response_model=AttributeCategoryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{category_id}",
        delete_attribute_category,
        methods=["DELETE"],
        response_model=DeleteAttributeCategoryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    return router


def _to_attribute_category_schema(category: AttributeCategory) -> AttributeCategorySchema:
    return AttributeCategorySchema(
        id=UUID(str(category.id)),
        external_id=category.external_id,
        label=category.label,
        flags=dict(category.flags),
        status=category.status,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


def _category_label_update_from_request(
    request: UpdateAttributeCategoryRequest,
) -> AttributeCategoryLabelUpdate:
    if "label" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_CATEGORY_FIELD

    return request.label or ""


def _category_flags_update_from_request(
    request: UpdateAttributeCategoryRequest,
) -> AttributeCategoryFlagsUpdate:
    if "flags" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_CATEGORY_FIELD

    return request.flags or {}
