"""HTTP document type catalog endpoints for the DocMind.ai API service."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from docmind_api.api.auth.dependencies import (
    require_cookie_csrf_protection,
    require_permissions,
)
from docmind_api.api.document_types.schemas import (
    CreateDocumentTypeRequest,
    DeleteDocumentTypeEnvelope,
    DeleteDocumentTypeSchema,
    DocumentTypeEnvelope,
    DocumentTypeExtensionValueRequest,
    DocumentTypeExtensionValueSchema,
    DocumentTypeListEnvelope,
    DocumentTypeListMetaSchema,
    DocumentTypeListSchema,
    DocumentTypeOverviewParameterSchema,
    DocumentTypeSchema,
    UpdateDocumentTypeRequest,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.application.document_types.ports import (
    DocumentTypeExtensionValuePayload,
    DocumentTypeReadModel,
)
from docmind_api.application.document_types.service import (
    PRESERVE_DOCUMENT_TYPE_DESCRIPTION,
    PRESERVE_DOCUMENT_TYPE_EXTENSION_VALUES,
    PRESERVE_DOCUMENT_TYPE_EXTERNAL_ID,
    CreateDocumentTypeCommand,
    DeactivateDocumentTypeCommand,
    DeleteDocumentTypeCommand,
    DocumentTypeCatalogService,
    DocumentTypeDescriptionUpdate,
    DocumentTypeExtensionValuesUpdate,
    DocumentTypeExternalIdUpdate,
    DocumentTypeListStatus,
    UpdateDocumentTypeCommand,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission

DocumentTypeCatalogServiceDependency = Callable[..., DocumentTypeCatalogService]
UserSessionServiceDependency = Callable[..., UserSessionService]


def create_document_types_router(
    *,
    document_type_catalog_dependency: DocumentTypeCatalogServiceDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create the document type catalog router."""

    router = APIRouter(prefix="/document-types", tags=["document-types"])
    require_admin_settings_manage = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def create_document_type(
        request: CreateDocumentTypeRequest,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            DocumentTypeCatalogService,
            Depends(document_type_catalog_dependency),
        ],
    ) -> DocumentTypeEnvelope:
        document_type = await catalog.create_document_type(
            CreateDocumentTypeCommand(
                external_id=request.external_id,
                name=request.name,
                description=request.description,
                extension_values=_extension_values_from_request(request.extension_values),
            ),
        )
        return DocumentTypeEnvelope(
            data=_to_document_type_schema(await catalog.build_read_model(document_type)),
        )

    async def list_document_types(
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            DocumentTypeCatalogService,
            Depends(document_type_catalog_dependency),
        ],
        status: Annotated[
            DocumentTypeListStatus,
            Query(description="Filter document types by lifecycle status."),
        ] = DocumentTypeListStatus.ACTIVE,
    ) -> DocumentTypeListEnvelope:
        result = await catalog.list_document_types(status=status)
        read_models = await catalog.build_read_models(result.document_types)
        return DocumentTypeListEnvelope(
            data=DocumentTypeListSchema(
                document_types=[_to_document_type_schema(read_model) for read_model in read_models],
            ),
            meta=DocumentTypeListMetaSchema(
                total_count=result.total_count,
                active_count=result.active_count,
                inactive_count=result.inactive_count,
                returned_count=result.returned_count,
                status=result.status,
            ),
        )

    async def update_document_type(
        document_type_id: UUID,
        request: UpdateDocumentTypeRequest,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            DocumentTypeCatalogService,
            Depends(document_type_catalog_dependency),
        ],
    ) -> DocumentTypeEnvelope:
        document_type = await catalog.update_document_type(
            UpdateDocumentTypeCommand(
                document_type_id=document_type_id,
                external_id=_external_id_update_from_request(request),
                name=request.name,
                description=_description_update_from_request(request),
                extension_values=_extension_values_update_from_request(request),
            ),
        )
        return DocumentTypeEnvelope(
            data=_to_document_type_schema(await catalog.build_read_model(document_type)),
        )

    async def deactivate_document_type(
        document_type_id: UUID,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            DocumentTypeCatalogService,
            Depends(document_type_catalog_dependency),
        ],
    ) -> DocumentTypeEnvelope:
        document_type = await catalog.deactivate_document_type(
            DeactivateDocumentTypeCommand(document_type_id=document_type_id),
        )
        return DocumentTypeEnvelope(
            data=_to_document_type_schema(await catalog.build_read_model(document_type)),
        )

    async def delete_document_type(
        document_type_id: UUID,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            DocumentTypeCatalogService,
            Depends(document_type_catalog_dependency),
        ],
    ) -> DeleteDocumentTypeEnvelope:
        result = await catalog.delete_document_type(
            DeleteDocumentTypeCommand(document_type_id=document_type_id),
        )
        return DeleteDocumentTypeEnvelope(
            data=DeleteDocumentTypeSchema(id=result.document_type_id, deleted=result.deleted),
        )

    router.add_api_route(
        "",
        create_document_type,
        methods=["POST"],
        status_code=HTTPStatus.CREATED,
        response_model=DocumentTypeEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "",
        list_document_types,
        methods=["GET"],
        response_model=DocumentTypeListEnvelope,
    )
    router.add_api_route(
        "/{document_type_id}",
        update_document_type,
        methods=["PATCH"],
        response_model=DocumentTypeEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{document_type_id}/deactivate",
        deactivate_document_type,
        methods=["POST"],
        response_model=DocumentTypeEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{document_type_id}",
        delete_document_type,
        methods=["DELETE"],
        response_model=DeleteDocumentTypeEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    return router


def _to_document_type_schema(read_model: DocumentTypeReadModel) -> DocumentTypeSchema:
    document_type = read_model.document_type
    return DocumentTypeSchema(
        id=UUID(str(document_type.id)),
        external_id=document_type.external_id,
        name=document_type.name,
        description=document_type.description,
        status=document_type.status,
        created_at=document_type.created_at,
        updated_at=document_type.updated_at,
        displayLabel=read_model.display_label,
        extensionValues=[
            DocumentTypeExtensionValueSchema(
                extensionFieldId=value.extension_field_id,
                code=value.code,
                label=value.label,
                valueType=value.value_type,
                dictionaryId=value.dictionary_id,
                dictionaryEntryId=value.dictionary_entry_id,
                textValue=value.text_value,
                displayValue=value.display_value,
                showInOverview=value.show_in_overview,
                fieldOrder=value.field_order,
            )
            for value in read_model.extension_values
        ],
        parameters=[
            DocumentTypeOverviewParameterSchema(
                code=parameter.code,
                label=parameter.label,
                value=parameter.value,
            )
            for parameter in read_model.parameters
        ],
        displayModeId=read_model.display_mode_id,
    )


def _external_id_update_from_request(
    request: UpdateDocumentTypeRequest,
) -> DocumentTypeExternalIdUpdate:
    if "external_id" not in request.model_fields_set:
        return PRESERVE_DOCUMENT_TYPE_EXTERNAL_ID

    return request.external_id


def _description_update_from_request(
    request: UpdateDocumentTypeRequest,
) -> DocumentTypeDescriptionUpdate:
    if "description" not in request.model_fields_set:
        return PRESERVE_DOCUMENT_TYPE_DESCRIPTION

    return request.description


def _extension_values_update_from_request(
    request: UpdateDocumentTypeRequest,
) -> DocumentTypeExtensionValuesUpdate:
    if "extension_values" not in request.model_fields_set:
        return PRESERVE_DOCUMENT_TYPE_EXTENSION_VALUES

    return _extension_values_from_request(request.extension_values)


def _extension_values_from_request(
    values: list[DocumentTypeExtensionValueRequest],
) -> tuple[DocumentTypeExtensionValuePayload, ...]:
    return tuple(
        DocumentTypeExtensionValuePayload(
            extension_field_id=value.extension_field_id,
            dictionary_entry_id=value.dictionary_entry_id,
            text_value=value.text_value,
        )
        for value in values
    )
