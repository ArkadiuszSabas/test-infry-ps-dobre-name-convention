"""HTTP system catalog endpoints for the DocMind.ai API service."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from docmind_api.api.auth.dependencies import (
    require_cookie_csrf_protection,
    require_permissions,
)
from docmind_api.api.system_catalogs.schemas import (
    SaveSystemCatalogDefinitionRequest,
    SystemCatalogDefinitionEnvelope,
    SystemCatalogDefinitionPayload,
    SystemCatalogDisplayModePartSchema,
    SystemCatalogDisplayModeSchema,
    SystemCatalogExtensionFieldSchema,
    SystemCatalogOptionExtensionValueSchema,
    SystemCatalogOptionParameterSchema,
    SystemCatalogOptionSchema,
    SystemCatalogOptionsEnvelope,
    SystemCatalogOptionsMeta,
    SystemCatalogOptionsPayload,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.application.document_types.ports import SystemCatalogOptionReadModel
from docmind_api.application.document_types.service import DocumentTypeCatalogService
from docmind_api.application.system_catalogs.service import (
    SaveSystemCatalogDefinitionCommand,
    SaveSystemCatalogDisplayModeCommand,
    SaveSystemCatalogDisplayModePartCommand,
    SaveSystemCatalogExtensionFieldCommand,
    SystemCatalogDefinition,
    SystemCatalogDefinitionService,
)
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission

SystemCatalogDefinitionServiceDependency = Callable[..., SystemCatalogDefinitionService]
DocumentTypeCatalogServiceDependency = Callable[..., DocumentTypeCatalogService]
UserSessionServiceDependency = Callable[..., UserSessionService]


def create_system_catalogs_router(
    *,
    system_catalog_definition_dependency: SystemCatalogDefinitionServiceDependency,
    document_type_catalog_dependency: DocumentTypeCatalogServiceDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create the system catalog router."""

    router = APIRouter(prefix="/system-catalogs", tags=["system-catalogs"])
    require_admin_settings_manage = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)
    require_documents_read = require_permissions(Permission.DOCUMENTS_READ)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def get_definition(
        system_catalog_key: str,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            SystemCatalogDefinitionService,
            Depends(system_catalog_definition_dependency),
        ],
    ) -> SystemCatalogDefinitionEnvelope:
        definition = await catalog.get_definition(system_catalog_key)
        return _definition_envelope(definition)

    async def save_definition(
        system_catalog_key: str,
        request: SaveSystemCatalogDefinitionRequest,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        catalog: Annotated[
            SystemCatalogDefinitionService,
            Depends(system_catalog_definition_dependency),
        ],
    ) -> SystemCatalogDefinitionEnvelope:
        definition = await catalog.save_definition(
            SaveSystemCatalogDefinitionCommand(
                system_catalog_key=system_catalog_key,
                fields=tuple(
                    SaveSystemCatalogExtensionFieldCommand(
                        id=field.id,
                        code=field.code,
                        label=field.label,
                        value_type=field.value_type,
                        dictionary_id=field.dictionary_id,
                        mapped_attribute_definition_id=field.mapped_attribute_definition_id,
                        is_required=field.is_required,
                        show_in_overview=field.show_in_overview,
                        field_order=field.field_order,
                        is_active=field.is_active,
                    )
                    for field in request.fields
                ),
                display_modes=tuple(
                    SaveSystemCatalogDisplayModeCommand(
                        id=mode.id,
                        name=mode.name,
                        is_default=mode.is_default,
                        is_active=mode.is_active,
                        parts=tuple(
                            SaveSystemCatalogDisplayModePartCommand(
                                id=part.id,
                                part_order=part.part_order,
                                source_type=part.source_type,
                                extension_field_id=part.extension_field_id,
                                extension_field_code=part.extension_field_code,
                                separator_before=part.separator_before,
                            )
                            for part in mode.parts
                        ),
                    )
                    for mode in request.display_modes
                ),
            ),
        )
        return _definition_envelope(definition)

    async def list_options(
        system_catalog_key: str,
        _reader_actor: Annotated[AuthenticatedActor, Depends(require_documents_read)],
        definition_catalog: Annotated[
            SystemCatalogDefinitionService,
            Depends(system_catalog_definition_dependency),
        ],
        document_types: Annotated[
            DocumentTypeCatalogService,
            Depends(document_type_catalog_dependency),
        ],
    ) -> SystemCatalogOptionsEnvelope:
        definition = await definition_catalog.get_definition(system_catalog_key)
        options = await document_types.list_system_catalog_options()
        return SystemCatalogOptionsEnvelope(
            data=SystemCatalogOptionsPayload(
                definition=_options_definition_payload(definition),
                options=[_option_schema(option) for option in options],
            ),
            meta=SystemCatalogOptionsMeta(
                systemCatalogKey=definition.system_catalog_key,
                returnedCount=len(options),
            ),
        )

    router.add_api_route(
        "/{system_catalog_key}/definition",
        get_definition,
        methods=["GET"],
        response_model=SystemCatalogDefinitionEnvelope,
    )
    router.add_api_route(
        "/{system_catalog_key}/definition",
        save_definition,
        methods=["PUT"],
        response_model=SystemCatalogDefinitionEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
    )
    router.add_api_route(
        "/{system_catalog_key}/options",
        list_options,
        methods=["GET"],
        response_model=SystemCatalogOptionsEnvelope,
    )
    return router


def _definition_envelope(definition: SystemCatalogDefinition) -> SystemCatalogDefinitionEnvelope:
    return SystemCatalogDefinitionEnvelope(
        data=_definition_payload(definition),
    )


def _option_schema(option: SystemCatalogOptionReadModel) -> SystemCatalogOptionSchema:
    return SystemCatalogOptionSchema(
        id=option.id,
        label=option.label,
        name=option.name,
        extensionValues=[
            SystemCatalogOptionExtensionValueSchema(
                extensionFieldId=value.extension_field_id,
                displayValue=value.display_value,
                textValue=value.text_value,
            )
            for value in option.extension_values
        ],
        parameters=[
            SystemCatalogOptionParameterSchema(
                code=parameter.code,
                label=parameter.label,
                value=parameter.value,
            )
            for parameter in option.parameters
        ],
        displayModeId=option.display_mode_id,
    )


def _definition_payload(definition: SystemCatalogDefinition) -> SystemCatalogDefinitionPayload:
    return SystemCatalogDefinitionPayload(
        systemCatalogKey=definition.system_catalog_key,
        fields=[
            SystemCatalogExtensionFieldSchema(
                id=UUID(str(field.id)),
                systemCatalogKey=field.system_catalog_key,
                code=field.code,
                label=field.label,
                valueType=field.value_type,
                dictionaryId=(
                    UUID(str(field.dictionary_id)) if field.dictionary_id is not None else None
                ),
                mappedAttributeDefinitionId=(
                    UUID(str(field.mapped_attribute_definition_id))
                    if field.mapped_attribute_definition_id is not None
                    else None
                ),
                isRequired=field.is_required,
                showInOverview=field.show_in_overview,
                fieldOrder=field.field_order,
                isActive=field.is_active,
                created_at=field.created_at,
                updated_at=field.updated_at,
            )
            for field in definition.fields
        ],
        displayModes=[
            SystemCatalogDisplayModeSchema(
                id=UUID(str(mode.id)),
                systemCatalogKey=mode.system_catalog_key,
                name=mode.name,
                isDefault=mode.is_default,
                isActive=mode.is_active,
                created_at=mode.created_at,
                updated_at=mode.updated_at,
                parts=[
                    SystemCatalogDisplayModePartSchema(
                        id=UUID(str(part.id)),
                        displayModeId=UUID(str(part.display_mode_id)),
                        partOrder=part.part_order,
                        sourceType=part.source_type,
                        extensionFieldId=(
                            UUID(str(part.extension_field_id))
                            if part.extension_field_id is not None
                            else None
                        ),
                        separatorBefore=part.separator_before,
                    )
                    for part in mode.parts
                ],
            )
            for mode in definition.display_modes
        ],
    )


def _options_definition_payload(
    definition: SystemCatalogDefinition,
) -> SystemCatalogDefinitionPayload:
    return SystemCatalogDefinitionPayload(
        systemCatalogKey=definition.system_catalog_key,
        fields=[],
        displayModes=[
            SystemCatalogDisplayModeSchema(
                id=UUID(str(mode.id)),
                systemCatalogKey=mode.system_catalog_key,
                name=mode.name,
                isDefault=mode.is_default,
                isActive=mode.is_active,
                created_at=mode.created_at,
                updated_at=mode.updated_at,
                parts=[
                    SystemCatalogDisplayModePartSchema(
                        id=UUID(str(part.id)),
                        displayModeId=UUID(str(part.display_mode_id)),
                        partOrder=part.part_order,
                        sourceType=part.source_type,
                        extensionFieldId=(
                            UUID(str(part.extension_field_id))
                            if part.extension_field_id is not None
                            else None
                        ),
                        separatorBefore=part.separator_before,
                    )
                    for part in mode.parts
                ],
            )
            for mode in definition.display_modes
            if mode.is_active
        ],
    )
