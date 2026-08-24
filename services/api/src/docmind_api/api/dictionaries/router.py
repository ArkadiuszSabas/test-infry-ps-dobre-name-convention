"""HTTP custom dictionary endpoints for the DocMind.ai API service."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from docmind_api.api.auth.dependencies import (
    require_cookie_csrf_protection,
    require_permissions,
)
from docmind_api.api.dictionaries.mappers import (
    to_dictionary_schema,
    to_entry_list_envelope,
    to_entry_schema,
    to_fields_envelope,
)
from docmind_api.api.dictionaries.schemas import (
    CreateDictionaryEntryRequest,
    CreateDictionaryRequest,
    DeleteDictionaryEntryEnvelope,
    DeleteDictionaryEntrySchema,
    DeleteDictionaryEnvelope,
    DeleteDictionarySchema,
    DictionaryEntryEnvelope,
    DictionaryEntryListEnvelope,
    DictionaryEnvelope,
    DictionaryFieldsEnvelope,
    DictionaryListEnvelope,
    DictionaryListMeta,
    DictionaryListSchema,
    SaveDictionaryFieldsRequest,
    UpdateDictionaryEntryRequest,
    UpdateDictionaryRequest,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.application.dictionaries.commands import (
    PRESERVE_DICTIONARY_FIELD,
    CreateDictionaryCommand,
    CreateDictionaryEntryCommand,
    DeactivateDictionaryCommand,
    DeactivateDictionaryEntryCommand,
    DeleteDictionaryCommand,
    DeleteDictionaryEntryCommand,
    DictionaryDescriptionUpdate,
    DictionaryEntryExternalIdUpdate,
    DictionaryEntryLabelUpdate,
    DictionaryEntryListStatus,
    DictionaryEntrySortOrderUpdate,
    DictionaryEntryValuesUpdate,
    DictionaryListStatus,
    DictionaryNameUpdate,
    ListDictionariesQuery,
    ListDictionaryEntriesQuery,
    SaveDictionaryFieldItem,
    SaveDictionaryFieldsCommand,
    UpdateDictionaryCommand,
    UpdateDictionaryEntryCommand,
)
from docmind_api.application.dictionaries.service import DictionaryCatalogService
from docmind_api.domain.attributes.models import AttributeConstraints, AttributeDataType
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission

DictionaryCatalogServiceDependency = Callable[..., DictionaryCatalogService]
UserSessionServiceDependency = Callable[..., UserSessionService]


def create_dictionaries_router(
    *,
    dictionary_catalog_dependency: DictionaryCatalogServiceDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create custom dictionary admin and lookup routes."""

    router = APIRouter(prefix="/dictionaries", tags=["dictionaries"])
    require_admin_settings_manage = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def create_dictionary(
        request: CreateDictionaryRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
    ) -> DictionaryEnvelope:
        dictionary = await catalog.create_dictionary(
            CreateDictionaryCommand(
                external_id=request.external_id,
                name=request.name,
                description=request.description,
            ),
        )
        return DictionaryEnvelope(data=to_dictionary_schema(dictionary))

    async def list_dictionaries(
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
        status: DictionaryListStatus = DictionaryListStatus.ACTIVE,
        search: str | None = None,
    ) -> DictionaryListEnvelope:
        dictionaries = await catalog.list_dictionaries(
            ListDictionariesQuery(status=status, search=search),
        )
        return DictionaryListEnvelope(
            data=DictionaryListSchema(
                dictionaries=[to_dictionary_schema(dictionary) for dictionary in dictionaries],
            ),
            meta=DictionaryListMeta(total_count=len(dictionaries)),
        )

    async def update_dictionary(
        dictionary_id: UUID,
        request: UpdateDictionaryRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
    ) -> DictionaryEnvelope:
        dictionary = await catalog.update_dictionary(
            UpdateDictionaryCommand(
                dictionary_id=dictionary_id,
                name=_dictionary_name_update_from_request(request),
                description=_dictionary_description_update_from_request(request),
            ),
        )
        return DictionaryEnvelope(data=to_dictionary_schema(dictionary))

    async def deactivate_dictionary(
        dictionary_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
    ) -> DictionaryEnvelope:
        dictionary = await catalog.deactivate_dictionary(
            DeactivateDictionaryCommand(dictionary_id=dictionary_id),
        )
        return DictionaryEnvelope(data=to_dictionary_schema(dictionary))

    async def delete_dictionary(
        dictionary_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
    ) -> DeleteDictionaryEnvelope:
        result = await catalog.delete_dictionary(
            DeleteDictionaryCommand(dictionary_id=dictionary_id)
        )
        return DeleteDictionaryEnvelope(
            data=DeleteDictionarySchema(id=result.dictionary_id, deleted=result.deleted),
        )

    async def list_fields(
        dictionary_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
    ) -> DictionaryFieldsEnvelope:
        fields = await catalog.list_fields(dictionary_id=dictionary_id)
        return to_fields_envelope(dictionary_id=dictionary_id, fields=fields)

    async def save_fields(
        dictionary_id: UUID,
        request: SaveDictionaryFieldsRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
    ) -> DictionaryFieldsEnvelope:
        fields = await catalog.save_fields(
            SaveDictionaryFieldsCommand(
                dictionary_id=dictionary_id,
                fields=tuple(
                    SaveDictionaryFieldItem(
                        external_id=item.external_id,
                        label=item.label,
                        data_type=AttributeDataType(item.data_type.value),
                        required=item.required,
                        constraints=AttributeConstraints.from_mapping(
                            item.constraints.model_dump(exclude_none=True),
                        ),
                        normalization=item.normalization,
                        format=item.format,
                        is_unique=item.is_unique,
                        sort_order=item.sort_order,
                        status=item.status,
                    )
                    for item in request.fields
                ),
            ),
        )
        return to_fields_envelope(dictionary_id=dictionary_id, fields=fields)

    async def create_entry(
        dictionary_id: UUID,
        request: CreateDictionaryEntryRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
    ) -> DictionaryEntryEnvelope:
        entry = await catalog.create_entry(
            CreateDictionaryEntryCommand(
                dictionary_id=dictionary_id,
                external_id=request.external_id,
                label=request.label,
                values=request.values,
                sort_order=request.sort_order,
            ),
        )
        return DictionaryEntryEnvelope(data=to_entry_schema(entry))

    async def list_entries(
        dictionary_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
        status: DictionaryEntryListStatus = DictionaryEntryListStatus.ACTIVE,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DictionaryEntryListEnvelope:
        page = await catalog.list_entries(
            ListDictionaryEntriesQuery(
                dictionary_id=dictionary_id,
                status=status,
                search=search,
                limit=limit,
                offset=offset,
            ),
        )
        return to_entry_list_envelope(dictionary_id=dictionary_id, page=page)

    async def update_entry(
        dictionary_id: UUID,
        entry_id: UUID,
        request: UpdateDictionaryEntryRequest,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
    ) -> DictionaryEntryEnvelope:
        entry = await catalog.update_entry(
            UpdateDictionaryEntryCommand(
                dictionary_id=dictionary_id,
                entry_id=entry_id,
                external_id=_entry_external_id_update_from_request(request),
                label=_entry_label_update_from_request(request),
                values=_entry_values_update_from_request(request),
                sort_order=_entry_sort_order_update_from_request(request),
            ),
        )
        return DictionaryEntryEnvelope(data=to_entry_schema(entry))

    async def deactivate_entry(
        dictionary_id: UUID,
        entry_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
    ) -> DictionaryEntryEnvelope:
        entry = await catalog.deactivate_entry(
            DeactivateDictionaryEntryCommand(dictionary_id=dictionary_id, entry_id=entry_id),
        )
        return DictionaryEntryEnvelope(data=to_entry_schema(entry))

    async def delete_entry(
        dictionary_id: UUID,
        entry_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[DictionaryCatalogService, Depends(dictionary_catalog_dependency)],
    ) -> DeleteDictionaryEntryEnvelope:
        result = await catalog.delete_entry(
            DeleteDictionaryEntryCommand(dictionary_id=dictionary_id, entry_id=entry_id),
        )
        return DeleteDictionaryEntryEnvelope(
            data=DeleteDictionaryEntrySchema(id=result.entry_id, deleted=result.deleted),
        )

    router.add_api_route(
        "",
        create_dictionary,
        methods=["POST"],
        status_code=HTTPStatus.CREATED,
        response_model=DictionaryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "",
        list_dictionaries,
        methods=["GET"],
        response_model=DictionaryListEnvelope,
    )
    router.add_api_route(
        "/{dictionary_id}",
        update_dictionary,
        methods=["PATCH"],
        response_model=DictionaryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{dictionary_id}/deactivate",
        deactivate_dictionary,
        methods=["POST"],
        response_model=DictionaryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{dictionary_id}",
        delete_dictionary,
        methods=["DELETE"],
        response_model=DeleteDictionaryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{dictionary_id}/fields",
        list_fields,
        methods=["GET"],
        response_model=DictionaryFieldsEnvelope,
    )
    router.add_api_route(
        "/{dictionary_id}/fields",
        save_fields,
        methods=["PATCH"],
        response_model=DictionaryFieldsEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{dictionary_id}/entries",
        create_entry,
        methods=["POST"],
        status_code=HTTPStatus.CREATED,
        response_model=DictionaryEntryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{dictionary_id}/entries",
        list_entries,
        methods=["GET"],
        response_model=DictionaryEntryListEnvelope,
    )
    router.add_api_route(
        "/{dictionary_id}/entries/{entry_id}",
        update_entry,
        methods=["PATCH"],
        response_model=DictionaryEntryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{dictionary_id}/entries/{entry_id}/deactivate",
        deactivate_entry,
        methods=["POST"],
        response_model=DictionaryEntryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{dictionary_id}/entries/{entry_id}",
        delete_entry,
        methods=["DELETE"],
        response_model=DeleteDictionaryEntryEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    return router


def _dictionary_name_update_from_request(request: UpdateDictionaryRequest) -> DictionaryNameUpdate:
    if "name" not in request.model_fields_set:
        return PRESERVE_DICTIONARY_FIELD
    return request.name or ""


def _dictionary_description_update_from_request(
    request: UpdateDictionaryRequest,
) -> DictionaryDescriptionUpdate:
    if "description" not in request.model_fields_set:
        return PRESERVE_DICTIONARY_FIELD
    return request.description


def _entry_external_id_update_from_request(
    request: UpdateDictionaryEntryRequest,
) -> DictionaryEntryExternalIdUpdate:
    if "external_id" not in request.model_fields_set:
        return PRESERVE_DICTIONARY_FIELD
    return request.external_id or ""


def _entry_label_update_from_request(
    request: UpdateDictionaryEntryRequest,
) -> DictionaryEntryLabelUpdate:
    if "label" not in request.model_fields_set:
        return PRESERVE_DICTIONARY_FIELD
    return request.label or ""


def _entry_values_update_from_request(
    request: UpdateDictionaryEntryRequest,
) -> DictionaryEntryValuesUpdate:
    if "values" not in request.model_fields_set:
        return PRESERVE_DICTIONARY_FIELD
    return request.values or {}


def _entry_sort_order_update_from_request(
    request: UpdateDictionaryEntryRequest,
) -> DictionaryEntrySortOrderUpdate:
    if "sort_order" not in request.model_fields_set:
        return PRESERVE_DICTIONARY_FIELD
    return request.sort_order
