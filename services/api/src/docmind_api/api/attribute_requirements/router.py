"""HTTP endpoints for document type attribute requirement configuration."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from docmind_api.api.attribute_requirements.schemas import (
    AttributeAssignmentEnvelope,
    AttributeAssignmentMetaSchema,
    AttributeAssignmentPayloadSchema,
    AttributeAssignmentSchema,
    AttributeRequirementAttributeSchema,
    AttributeRequirementDocumentTypeSchema,
    AttributeRequirementMatrixEnvelope,
    AttributeRequirementMatrixMetaSchema,
    AttributeRequirementMatrixSchema,
    AttributeRequirementSchema,
    MetadataSchemaDocumentTypeSchema,
    MetadataSchemaEnvelope,
    MetadataSchemaFieldSchema,
    MetadataSchemaMetaSchema,
    MetadataSchemaPayloadSchema,
    SaveAttributeAssignmentsRequest,
    SaveAttributeRequirementsRequest,
)
from docmind_api.api.auth.dependencies import (
    require_cookie_csrf_protection,
    require_permissions,
)
from docmind_api.application.attribute_requirements.models import (
    AttributeRequirementEntry,
    DocumentTypeAttributeRequirementMatrix,
    DocumentTypeMetadataSchema,
    SaveAttributeDocumentTypeAssignmentItem,
    SaveAttributeDocumentTypeAssignmentsCommand,
    SaveAttributeRequirementItem,
    SaveDocumentTypeAttributeRequirementsCommand,
)
from docmind_api.application.attribute_requirements.service import (
    AttributeRequirementMatrixService,
)
from docmind_api.application.auth.sessions import UserSessionService
from docmind_api.domain.attributes.models import ATTRIBUTE_CATEGORY_DEFAULT, AttributeDefinition
from docmind_api.domain.auth.actors import AuthenticatedActor, Permission
from docmind_api.domain.document_types.models import DocumentType

AttributeRequirementMatrixServiceDependency = Callable[..., AttributeRequirementMatrixService]
UserSessionServiceDependency = Callable[..., UserSessionService]


def create_attribute_requirements_router(
    *,
    attribute_requirement_matrix_dependency: AttributeRequirementMatrixServiceDependency,
    user_session_service_dependency: UserSessionServiceDependency,
    allowed_browser_origins: tuple[str, ...],
) -> APIRouter:
    """Create the document type attribute requirement router."""

    # Keep both matrix directions on the same public router.  The explicit prefix on
    # document-type routes avoids coupling the attribute-oriented API to that path.
    router = APIRouter()
    require_admin_settings_manage = require_permissions(Permission.ADMIN_SETTINGS_MANAGE)
    require_documents_read = require_permissions(Permission.DOCUMENTS_READ)
    cookie_csrf_protection = require_cookie_csrf_protection(
        allowed_browser_origins,
        user_session_service_dependency,
    )

    async def get_attribute_requirements(
        document_type_id: UUID,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        matrix_service: Annotated[
            AttributeRequirementMatrixService,
            Depends(attribute_requirement_matrix_dependency),
        ],
    ) -> AttributeRequirementMatrixEnvelope:
        matrix = await matrix_service.get_matrix(document_type_id=document_type_id)
        return _to_matrix_envelope(matrix)

    async def get_attribute_assignments(
        attribute_id: UUID,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        matrix_service: Annotated[
            AttributeRequirementMatrixService, Depends(attribute_requirement_matrix_dependency)
        ],
    ) -> AttributeAssignmentEnvelope:
        (
            attribute,
            document_types,
            requirements,
            version,
            is_metadata,
        ) = await matrix_service.get_attribute_assignments(attribute_id=attribute_id)
        by_type = {UUID(str(r.document_type_id)): r for r in requirements}
        assignments: list[AttributeAssignmentSchema] = []
        for document_type in document_types:
            requirement = by_type.get(UUID(str(document_type.id)))
            assignments.append(
                AttributeAssignmentSchema(
                    document_type=_to_document_type_schema(document_type),
                    state=(
                        "required"
                        if requirement and requirement.required
                        else "optional"
                        if requirement
                        else "unassigned"
                    ),
                    requirement_id=UUID(str(requirement.id)) if requirement else None,
                    include_metadata_in_context_resolver=requirement.include_metadata_in_context_resolver
                    if requirement
                    else False,
                    missing_required_action=requirement.missing_required_action
                    if requirement
                    else None,
                    created_at=requirement.created_at if requirement else None,
                    updated_at=requirement.updated_at if requirement else None,
                )
            )
        return AttributeAssignmentEnvelope(
            data=AttributeAssignmentPayloadSchema(
                attribute=_to_attribute_schema(attribute, is_metadata=is_metadata),
                assignments=assignments,
            ),
            meta=AttributeAssignmentMetaSchema(
                total_count=len(assignments),
                assigned_count=len(requirements),
                unassigned_count=len(assignments) - len(requirements),
                required_count=sum(1 for r in requirements if r.required),
                optional_count=sum(1 for r in requirements if not r.required),
                version=version,
            ),
        )

    async def get_metadata_schema(
        document_type_id: UUID,
        _actor: Annotated[AuthenticatedActor, Depends(require_documents_read)],
        matrix_service: Annotated[
            AttributeRequirementMatrixService,
            Depends(attribute_requirement_matrix_dependency),
        ],
    ) -> MetadataSchemaEnvelope:
        schema = await matrix_service.get_metadata_schema(document_type_id=document_type_id)
        return _to_metadata_schema_envelope(schema)

    async def save_attribute_assignments(
        attribute_id: UUID,
        request: SaveAttributeAssignmentsRequest,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        matrix_service: Annotated[
            AttributeRequirementMatrixService,
            Depends(attribute_requirement_matrix_dependency),
        ],
    ) -> AttributeAssignmentEnvelope:
        await matrix_service.save_attribute_assignments(
            attribute_id=attribute_id,
            command=SaveAttributeDocumentTypeAssignmentsCommand(
                attribute_id=attribute_id,
                base_version=request.base_version,
                assignments=tuple(
                    SaveAttributeDocumentTypeAssignmentItem(
                        document_type_id=item.document_type_id,
                        required=item.required,
                        include_metadata_in_context_resolver=item.include_metadata_in_context_resolver,
                        missing_required_action=item.missing_required_action,
                    )
                    for item in request.assignments
                ),
            ),
        )
        return await get_attribute_assignments(attribute_id, _admin_actor, matrix_service)

    async def save_attribute_requirements(
        document_type_id: UUID,
        request: SaveAttributeRequirementsRequest,
        _admin_actor: Annotated[AuthenticatedActor, Depends(require_admin_settings_manage)],
        matrix_service: Annotated[
            AttributeRequirementMatrixService,
            Depends(attribute_requirement_matrix_dependency),
        ],
    ) -> AttributeRequirementMatrixEnvelope:
        matrix = await matrix_service.save_requirements(
            SaveDocumentTypeAttributeRequirementsCommand(
                document_type_id=document_type_id,
                requirements=tuple(
                    SaveAttributeRequirementItem(
                        attribute_definition_id=item.attribute_definition_id,
                        required=item.required,
                        include_metadata_in_context_resolver=item.include_metadata_in_context_resolver,
                        missing_required_action=item.missing_required_action,
                    )
                    for item in request.requirements
                ),
            ),
        )
        return _to_matrix_envelope(matrix)

    router.add_api_route(
        "/document-types/{document_type_id}/attribute-requirements",
        get_attribute_requirements,
        methods=["GET"],
        response_model=AttributeRequirementMatrixEnvelope,
        tags=["attribute-requirements"],
    )
    router.add_api_route(
        "/attributes/{attribute_id}/document-type-assignments",
        get_attribute_assignments,
        methods=["GET"],
        response_model=AttributeAssignmentEnvelope,
        tags=["attribute-requirements"],
    )
    router.add_api_route(
        "/attributes/{attribute_id}/document-type-assignments",
        save_attribute_assignments,
        methods=["PATCH"],
        response_model=AttributeAssignmentEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
        tags=["attribute-requirements"],
    )
    router.add_api_route(
        "/document-types/{document_type_id}/attribute-requirements",
        save_attribute_requirements,
        methods=["PATCH"],
        response_model=AttributeRequirementMatrixEnvelope,
        dependencies=[Depends(cookie_csrf_protection)],
        tags=["attribute-requirements"],
    )
    router.add_api_route(
        "/document-types/{document_type_id}/metadata-schema",
        get_metadata_schema,
        methods=["GET"],
        response_model=MetadataSchemaEnvelope,
        tags=["metadata-schema"],
    )
    return router


def _to_matrix_envelope(
    matrix: DocumentTypeAttributeRequirementMatrix,
) -> AttributeRequirementMatrixEnvelope:
    return AttributeRequirementMatrixEnvelope(
        data=AttributeRequirementMatrixSchema(
            document_type=_to_document_type_schema(matrix.document_type),
            requirements=[_to_requirement_schema(entry) for entry in matrix.requirements],
            unassigned_attributes=[
                _to_attribute_schema(
                    attribute,
                    is_metadata=UUID(str(attribute.id)) in matrix.metadata_attribute_ids,
                )
                for attribute in matrix.unassigned_attributes
            ],
        ),
        meta=AttributeRequirementMatrixMetaSchema(
            document_type_id=UUID(str(matrix.document_type.id)),
            total_attribute_count=matrix.total_attribute_count,
            assigned_attribute_count=matrix.assigned_attribute_count,
            required_attribute_count=matrix.required_attribute_count,
            optional_attribute_count=matrix.optional_attribute_count,
            unassigned_attribute_count=matrix.unassigned_attribute_count,
        ),
    )


def _to_document_type_schema(
    document_type: DocumentType,
) -> AttributeRequirementDocumentTypeSchema:
    return AttributeRequirementDocumentTypeSchema(
        id=UUID(str(document_type.id)),
        external_id=document_type.external_id,
        name=document_type.name,
        status=document_type.status,
    )


def _to_requirement_schema(entry: AttributeRequirementEntry) -> AttributeRequirementSchema:
    return AttributeRequirementSchema(
        id=UUID(str(entry.requirement.id)),
        external_id=entry.requirement.external_id,
        attribute=_to_attribute_schema(entry.attribute, is_metadata=entry.is_metadata),
        required=entry.requirement.required,
        include_metadata_in_context_resolver=entry.requirement.include_metadata_in_context_resolver,
        missing_required_action=entry.requirement.missing_required_action,
        created_at=entry.requirement.created_at,
        updated_at=entry.requirement.updated_at,
    )


def _to_attribute_schema(
    attribute: AttributeDefinition,
    *,
    is_metadata: bool = False,
) -> AttributeRequirementAttributeSchema:
    return AttributeRequirementAttributeSchema(
        id=UUID(str(attribute.id)),
        external_id=attribute.external_id,
        name=attribute.name,
        category=attribute.category or ATTRIBUTE_CATEGORY_DEFAULT,
        status=attribute.status,
        is_metadata=is_metadata,
    )


def _to_metadata_schema_envelope(
    schema: DocumentTypeMetadataSchema,
) -> MetadataSchemaEnvelope:
    return MetadataSchemaEnvelope(
        data=MetadataSchemaPayloadSchema(
            document_type=MetadataSchemaDocumentTypeSchema(
                id=UUID(str(schema.document_type.id)),
                external_id=schema.document_type.external_id,
                name=schema.document_type.name,
                status=schema.document_type.status,
            ),
            fields=[_to_metadata_schema_field(entry) for entry in schema.fields],
        ),
        meta=MetadataSchemaMetaSchema(
            document_type_id=UUID(str(schema.document_type.id)),
            field_count=schema.field_count,
            required_field_count=schema.required_field_count,
            optional_field_count=schema.optional_field_count,
        ),
    )


def _to_metadata_schema_field(entry: AttributeRequirementEntry) -> MetadataSchemaFieldSchema:
    return MetadataSchemaFieldSchema(
        id=UUID(str(entry.attribute.id)),
        external_id=entry.attribute.external_id,
        key=entry.attribute.external_id or str(entry.attribute.id),
        label=entry.attribute.name,
        category=entry.attribute.category or ATTRIBUTE_CATEGORY_DEFAULT,
        data_type=entry.attribute.data_type,
        required=entry.requirement.required,
        constraints=entry.attribute.constraints.as_json(),
        allowed_values=list(entry.attribute.allowed_values),
        value_source=entry.attribute.value_source,
        dictionary_id=(
            UUID(str(entry.attribute.dictionary_id))
            if entry.attribute.dictionary_id is not None
            else None
        ),
        status=entry.attribute.status,
        schema_version=entry.attribute.schema_version,
        created_at=entry.attribute.created_at,
        updated_at=entry.attribute.updated_at,
    )
