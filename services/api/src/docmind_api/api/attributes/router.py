"""HTTP attribute definition catalog endpoints for the DocMind.ai API service."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from docmind_api.api.attributes.schemas import (
    AttributeCategoryCountSchema,
    AttributeConstraintsRequest,
    AttributeDataTypeRequest,
    AttributeDefinitionEnvelope,
    AttributeDefinitionListEnvelope,
    AttributeDefinitionListMeta,
    AttributeDefinitionListSchema,
    AttributeDefinitionSchema,
    CreateAttributeDefinitionRequest,
    DeleteAttributeDefinitionEnvelope,
    DeleteAttributeDefinitionSchema,
    UpdateAttributeDefinitionRequest,
)
from docmind_api.api.auth.dependencies import (
    require_cookie_csrf_protection,
    require_permissions,
)
from docmind_api.application.attributes.errors import AttributeDefinitionValidationError
from docmind_api.application.attributes.service import (
    PRESERVE_ATTRIBUTE_FIELD,
    AttributeAllowedValuesUpdate,
    AttributeCategoryIdUpdate,
    AttributeCommentUpdate,
    AttributeConstraintsUpdate,
    AttributeDataTypeUpdate,
    AttributeDefinitionCatalogService,
    AttributeDefinitionList,
    AttributeDictionaryIdUpdate,
    AttributeExternalIdUpdate,
    AttributeLlmContextUpdate,
    AttributeNameUpdate,
    AttributeSourceUpdate,
    AttributeValueSourceUpdate,
    CreateAttributeDefinitionCommand,
    DeactivateAttributeDefinitionCommand,
    DeleteAttributeDefinitionCommand,
    ListAttributeDefinitionsQuery,
    UpdateAttributeDefinitionCommand,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.domain.attributes.models import (
    ATTRIBUTE_CATEGORY_DEFAULT,
    AttributeConstraints,
    AttributeDataType,
    AttributeDefinition,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission

AttributeDefinitionCatalogServiceDependency = Callable[..., AttributeDefinitionCatalogService]
UserSessionServiceDependency = Callable[..., UserSessionService]


def create_attributes_router(
    *,
    attribute_definition_catalog_dependency: AttributeDefinitionCatalogServiceDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create the attribute definition catalog router."""

    router = APIRouter(prefix="/attributes", tags=["attributes"])
    require_admin_settings_manage = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def create_attribute_definition(
        request: CreateAttributeDefinitionRequest,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            AttributeDefinitionCatalogService,
            Depends(attribute_definition_catalog_dependency),
        ],
    ) -> AttributeDefinitionEnvelope:
        attribute = await catalog.create_attribute_definition(
            CreateAttributeDefinitionCommand(
                external_id=request.external_id,
                name=request.name,
                source=request.source,
                category_id=request.category_id,
                data_type=_data_type_from_request(request.data_type),
                constraints=_constraints_from_request(request.constraints),
                allowed_values=tuple(request.allowed_values),
                value_source=request.value_source,
                dictionary_id=request.dictionary_id,
                comment=request.comment,
                llm_context=request.llm_context,
            ),
        )
        return AttributeDefinitionEnvelope(data=_to_attribute_definition_schema(attribute))

    async def list_attribute_definitions(
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            AttributeDefinitionCatalogService,
            Depends(attribute_definition_catalog_dependency),
        ],
        category: str | None = None,
    ) -> AttributeDefinitionListEnvelope:
        result = await catalog.list_attribute_definitions(
            ListAttributeDefinitionsQuery(category=category),
        )
        return _to_attribute_definition_list_envelope(result)

    async def update_attribute_definition(
        attribute_id: UUID,
        request: UpdateAttributeDefinitionRequest,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            AttributeDefinitionCatalogService,
            Depends(attribute_definition_catalog_dependency),
        ],
    ) -> AttributeDefinitionEnvelope:
        attribute = await catalog.update_attribute_definition(
            UpdateAttributeDefinitionCommand(
                attribute_id=attribute_id,
                external_id=_external_id_update_from_request(request),
                name=_name_update_from_request(request),
                category_id=_category_id_update_from_request(request),
                data_type=_data_type_update_from_request(request),
                constraints=_constraints_update_from_request(request),
                allowed_values=_allowed_values_update_from_request(request),
                value_source=_value_source_update_from_request(request),
                dictionary_id=_dictionary_id_update_from_request(request),
                source=_source_update_from_request(request),
                comment=_comment_update_from_request(request),
                llm_context=_llm_context_update_from_request(request),
            ),
        )
        return AttributeDefinitionEnvelope(data=_to_attribute_definition_schema(attribute))

    async def deactivate_attribute_definition(
        attribute_id: UUID,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            AttributeDefinitionCatalogService,
            Depends(attribute_definition_catalog_dependency),
        ],
    ) -> AttributeDefinitionEnvelope:
        attribute = await catalog.deactivate_attribute_definition(
            DeactivateAttributeDefinitionCommand(attribute_id=attribute_id),
        )
        return AttributeDefinitionEnvelope(data=_to_attribute_definition_schema(attribute))

    async def delete_attribute_definition(
        attribute_id: UUID,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            AttributeDefinitionCatalogService,
            Depends(attribute_definition_catalog_dependency),
        ],
    ) -> DeleteAttributeDefinitionEnvelope:
        result = await catalog.delete_attribute_definition(
            DeleteAttributeDefinitionCommand(attribute_id=attribute_id),
        )
        return DeleteAttributeDefinitionEnvelope(
            data=DeleteAttributeDefinitionSchema(id=result.attribute_id, deleted=result.deleted),
        )

    router.add_api_route(
        "",
        create_attribute_definition,
        methods=["POST"],
        status_code=HTTPStatus.CREATED,
        response_model=AttributeDefinitionEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "",
        list_attribute_definitions,
        methods=["GET"],
        response_model=AttributeDefinitionListEnvelope,
    )
    router.add_api_route(
        "/{attribute_id}",
        update_attribute_definition,
        methods=["PATCH"],
        response_model=AttributeDefinitionEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{attribute_id}/deactivate",
        deactivate_attribute_definition,
        methods=["POST"],
        response_model=AttributeDefinitionEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{attribute_id}",
        delete_attribute_definition,
        methods=["DELETE"],
        response_model=DeleteAttributeDefinitionEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    return router


def _to_attribute_definition_schema(
    attribute: AttributeDefinition,
) -> AttributeDefinitionSchema:
    return AttributeDefinitionSchema(
        id=UUID(str(attribute.id)),
        external_id=attribute.external_id,
        name=attribute.name,
        category=attribute.category or ATTRIBUTE_CATEGORY_DEFAULT,
        category_id=(
            UUID(str(attribute.category_id)) if attribute.category_id is not None else None
        ),
        data_type=attribute.data_type,
        constraints=attribute.constraints.as_json(),
        allowed_values=list(attribute.allowed_values),
        value_source=attribute.value_source,
        dictionary_id=(
            UUID(str(attribute.dictionary_id)) if attribute.dictionary_id is not None else None
        ),
        source=attribute.source,
        comment=attribute.comment,
        llm_context=attribute.llm_context,
        status=attribute.status,
        schema_version=attribute.schema_version,
        created_at=attribute.created_at,
        updated_at=attribute.updated_at,
    )


def _to_attribute_definition_list_envelope(
    result: AttributeDefinitionList,
) -> AttributeDefinitionListEnvelope:
    return AttributeDefinitionListEnvelope(
        data=AttributeDefinitionListSchema(
            attributes=[
                _to_attribute_definition_schema(attribute) for attribute in result.attributes
            ],
        ),
        meta=AttributeDefinitionListMeta(
            total_count=len(result.attributes),
            category_counts=[
                AttributeCategoryCountSchema(
                    category=category_count.category,
                    count=category_count.count,
                )
                for category_count in result.category_counts
            ],
        ),
    )


def _external_id_update_from_request(
    request: UpdateAttributeDefinitionRequest,
) -> AttributeExternalIdUpdate:
    if "external_id" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_FIELD

    return request.external_id


def _name_update_from_request(
    request: UpdateAttributeDefinitionRequest,
) -> AttributeNameUpdate:
    if "name" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_FIELD

    return request.name or ""


def _category_id_update_from_request(
    request: UpdateAttributeDefinitionRequest,
) -> AttributeCategoryIdUpdate:
    if "category_id" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_FIELD

    return request.category_id


def _allowed_values_update_from_request(
    request: UpdateAttributeDefinitionRequest,
) -> AttributeAllowedValuesUpdate:
    if "allowed_values" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_FIELD

    return tuple(request.allowed_values or ())


def _data_type_update_from_request(
    request: UpdateAttributeDefinitionRequest,
) -> AttributeDataTypeUpdate:
    if "data_type" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_FIELD

    if request.data_type is None:
        return PRESERVE_ATTRIBUTE_FIELD

    return _data_type_from_request(request.data_type)


def _value_source_update_from_request(
    request: UpdateAttributeDefinitionRequest,
) -> AttributeValueSourceUpdate:
    if "value_source" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_FIELD

    return request.value_source or PRESERVE_ATTRIBUTE_FIELD


def _dictionary_id_update_from_request(
    request: UpdateAttributeDefinitionRequest,
) -> AttributeDictionaryIdUpdate:
    if "dictionary_id" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_FIELD

    return request.dictionary_id


def _data_type_from_request(data_type: AttributeDataTypeRequest) -> AttributeDataType:
    return AttributeDataType(data_type.value)


def _constraints_update_from_request(
    request: UpdateAttributeDefinitionRequest,
) -> AttributeConstraintsUpdate:
    if "constraints" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_FIELD

    if request.constraints is None:
        return AttributeConstraints()

    return _constraints_from_request(request.constraints)


def _source_update_from_request(
    request: UpdateAttributeDefinitionRequest,
) -> AttributeSourceUpdate:
    if "source" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_FIELD

    return request.source or PRESERVE_ATTRIBUTE_FIELD


def _comment_update_from_request(
    request: UpdateAttributeDefinitionRequest,
) -> AttributeCommentUpdate:
    if "comment" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_FIELD

    return request.comment


def _llm_context_update_from_request(
    request: UpdateAttributeDefinitionRequest,
) -> AttributeLlmContextUpdate:
    if "llm_context" not in request.model_fields_set:
        return PRESERVE_ATTRIBUTE_FIELD

    return request.llm_context


def _constraints_from_request(
    request: AttributeConstraintsRequest,
) -> AttributeConstraints:
    try:
        return AttributeConstraints.from_mapping(request.model_dump(exclude_none=True))
    except ValueError as error:
        raise AttributeDefinitionValidationError(message=str(error)) from error
