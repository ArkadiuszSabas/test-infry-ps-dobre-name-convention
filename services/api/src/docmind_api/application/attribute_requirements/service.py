"""Application use cases for document type attribute requirement configuration."""

import hashlib
from uuid import NAMESPACE_URL, UUID, uuid5

from docmind_api.application.attribute_requirements.models import (
    AttributeAssignmentVersionConflictError,
    AttributeRequirementConfigurationError,
    AttributeRequirementEntry,
    AttributeRequirementReferenceError,
    AttributeRequirementValidationError,
    DocumentTypeAttributeRequirementMatrix,
    DocumentTypeMetadataSchema,
    SaveAttributeDocumentTypeAssignmentsCommand,
    SaveAttributeRequirementItem,
    SaveDocumentTypeAttributeRequirementsCommand,
)
from docmind_api.application.attribute_requirements.ports import (
    AttributeRequirementIdFactory,
    AttributeRequirementRepository,
    Clock,
)
from docmind_api.application.attributes.errors import AttributeDefinitionNotFoundError
from docmind_api.application.attributes.ports import (
    AttributeCategoryRepository,
    AttributeDefinitionRepository,
)
from docmind_api.application.document_types.ports import DocumentTypeCatalogRepository
from docmind_api.application.document_types.service import (
    DocumentTypeNotFoundError,
    DocumentTypeValidationError,
)
from docmind_api.domain.attribute_requirements.models import (
    DocumentTypeAttributeRequirement,
)
from docmind_api.domain.attributes.models import (
    AttributeDefinition,
    attribute_category_is_metadata,
    normalize_attribute_external_id,
)
from docmind_api.domain.document_types.models import (
    DocumentType,
    DocumentTypeStatus,
    normalize_document_type_external_id,
)

__all__ = ["SaveAttributeRequirementItem"]


class AttributeRequirementMatrixService:
    """Application service for document type attribute requirement workflows."""

    def __init__(
        self,
        *,
        repository: AttributeRequirementRepository,
        document_type_repository: DocumentTypeCatalogRepository,
        attribute_repository: AttributeDefinitionRepository,
        attribute_category_repository: AttributeCategoryRepository,
        clock: Clock,
        id_factory: AttributeRequirementIdFactory | None = None,
    ) -> None:
        self._repository = repository
        self._document_type_repository = document_type_repository
        self._attribute_repository = attribute_repository
        self._attribute_category_repository = attribute_category_repository
        self._id_factory = id_factory
        self._clock = clock

    async def get_matrix(
        self,
        *,
        document_type_id: UUID | str,
    ) -> DocumentTypeAttributeRequirementMatrix:
        """Return a matrix preview for one document type."""

        document_type_reference = _validated_document_type_id(document_type_id)
        document_type = await self._get_document_type(document_type_reference)
        document_type_id = UUID(str(document_type.id))
        attributes = await self._attribute_repository.list()
        requirements = await self._repository.list_for_document_type(document_type_id)

        return await self._build_matrix(
            document_type=document_type,
            attributes=attributes,
            requirements=requirements,
        )

    async def get_attribute_assignments(
        self, *, attribute_id: UUID
    ) -> tuple[
        AttributeDefinition,
        tuple[DocumentType, ...],
        tuple[DocumentTypeAttributeRequirement, ...],
        str,
        bool,
    ]:
        attribute = await self._attribute_repository.get_by_id(attribute_id)
        if attribute is None:
            raise AttributeDefinitionNotFoundError(attribute_id=attribute_id)
        document_types = await self._document_type_repository.list_all()
        requirements = await self._repository.list_for_attribute(attribute_id)
        version = _attribute_assignments_version(requirements)
        return (
            attribute,
            document_types,
            requirements,
            version,
            _attribute_is_active_metadata(
                attribute,
                metadata_category_ids=await self._active_metadata_category_ids(),
            ),
        )

    async def save_attribute_assignments(
        self,
        *,
        attribute_id: UUID,
        command: SaveAttributeDocumentTypeAssignmentsCommand,
    ) -> str:
        await self._repository.lock_matrix_writes()
        attribute = await self._attribute_repository.get_by_id(attribute_id)
        if attribute is None:
            raise AttributeDefinitionNotFoundError(attribute_id=attribute_id)
        document_types = await self._document_type_repository.list_all()
        current_requirements = await self._repository.list_for_attribute(
            attribute_id, for_update=True
        )
        current_version = _attribute_assignments_version(current_requirements)
        if command.base_version != current_version:
            raise AttributeAssignmentVersionConflictError(
                current_version=current_version,
                current_assignments=tuple(
                    {
                        "document_type_id": str(requirement.document_type_id),
                        "state": "required" if requirement.required else "optional",
                        "requirement_id": str(requirement.id),
                        "include_metadata_in_context_resolver": (
                            requirement.include_metadata_in_context_resolver
                        ),
                        "missing_required_action": (
                            requirement.missing_required_action.value
                            if requirement.missing_required_action is not None
                            else None
                        ),
                        "created_at": requirement.created_at.isoformat(),
                        "updated_at": requirement.updated_at.isoformat(),
                    }
                    for requirement in current_requirements
                ),
            )
        by_id = {UUID(str(item.id)): item for item in document_types}
        seen: set[UUID] = set()
        timestamp = self._clock.now()
        saved: list[DocumentTypeAttributeRequirement] = []
        existing_by_type = {
            UUID(str(requirement.document_type_id)): requirement
            for requirement in current_requirements
        }
        metadata_category_ids = await self._active_metadata_category_ids()
        for item in command.assignments:
            document_type_id = item.document_type_id
            if document_type_id in seen or document_type_id not in by_id:
                raise AttributeRequirementValidationError(
                    message="Assignments contain an unknown or duplicate document type."
                )
            seen.add(document_type_id)
            document_type = by_id[document_type_id]
            if document_type.is_active and not attribute.is_active:
                raise AttributeRequirementValidationError(
                    message="Active document types cannot use inactive attributes."
                )
            is_metadata = _attribute_is_active_metadata(
                attribute, metadata_category_ids=metadata_category_ids
            )
            if item.include_metadata_in_context_resolver and not is_metadata:
                raise AttributeRequirementValidationError(
                    message="Only metadata attributes can be included in the Context Resolver."
                )
            existing = existing_by_type.get(document_type_id)
            try:
                saved.append(
                    DocumentTypeAttributeRequirement(
                        id=existing.id
                        if existing
                        else (self._id_factory.new_id() if self._id_factory else None),
                        external_id=existing.external_id
                        if existing
                        else _requirement_external_id(
                            document_type=document_type, attribute=attribute
                        ),
                        document_type_id=document_type_id,
                        attribute_definition_id=attribute.id,
                        required=item.required,
                        include_metadata_in_context_resolver=item.include_metadata_in_context_resolver,
                        missing_required_action=item.missing_required_action,
                        created_at=existing.created_at if existing else timestamp,
                        updated_at=timestamp,
                    )
                )
            except ValueError as error:
                raise AttributeRequirementValidationError(message=str(error)) from error
        await self._repository.replace_for_attribute(attribute_id, tuple(saved))
        return (await self.get_attribute_assignments(attribute_id=attribute_id))[3]

    async def get_metadata_schema(
        self,
        *,
        document_type_id: UUID | str,
    ) -> DocumentTypeMetadataSchema:
        """Return the typed metadata schema inherited by one document type."""

        matrix = await self.get_matrix(document_type_id=document_type_id)
        fields = tuple(entry for entry in matrix.requirements if entry.is_metadata)
        return DocumentTypeMetadataSchema(
            document_type=matrix.document_type,
            fields=fields,
        )

    async def save_requirements(
        self,
        command: SaveDocumentTypeAttributeRequirementsCommand,
    ) -> DocumentTypeAttributeRequirementMatrix:
        """Replace one document type's attribute requirement matrix."""

        await self._repository.lock_matrix_writes()
        document_type_reference = _validated_document_type_id(command.document_type_id)
        document_type = await self._get_document_type(document_type_reference)
        document_type_id = UUID(str(document_type.id))
        attributes = await self._attribute_repository.list()
        attributes_by_id = {UUID(str(attribute.id)): attribute for attribute in attributes}
        attributes_by_external_id = {
            attribute.external_id: attribute
            for attribute in attributes
            if attribute.external_id is not None
        }
        metadata_category_ids = await self._active_metadata_category_ids()

        timestamp = self._clock.now()
        requirements: list[DocumentTypeAttributeRequirement] = []
        missing_attribute_ids: list[str] = []
        seen_attribute_ids: set[UUID] = set()
        duplicate_attribute_ids: set[str] = set()
        for item in command.requirements:
            attribute_reference = _validated_attribute_definition_id(
                item.attribute_definition_id,
            )
            attribute = _attribute_by_reference(
                attributes_by_id=attributes_by_id,
                attributes_by_external_id=attributes_by_external_id,
                attribute_reference=attribute_reference,
            )
            if attribute is None:
                missing_attribute_ids.append(str(attribute_reference))
                continue
            attribute_definition_id = UUID(str(attribute.id))
            if attribute_definition_id in seen_attribute_ids:
                duplicate_attribute_ids.add(str(attribute_definition_id))
                continue
            seen_attribute_ids.add(attribute_definition_id)
            if document_type.status == DocumentTypeStatus.ACTIVE and not attribute.is_active:
                raise AttributeRequirementValidationError(
                    message=("Active document types cannot use inactive attribute definitions."),
                    details={"inactive_attribute_definition_ids": (str(attribute_definition_id),)},
                )
            is_metadata = _attribute_is_active_metadata(
                attribute,
                metadata_category_ids=metadata_category_ids,
            )
            if item.include_metadata_in_context_resolver and not is_metadata:
                raise AttributeRequirementValidationError(
                    message=(
                        "Only attributes in an active metadata category can be included "
                        "in OCR results."
                    ),
                    details={
                        "non_metadata_attribute_definition_ids": (str(attribute_definition_id),)
                    },
                )

            try:
                requirements.append(
                    DocumentTypeAttributeRequirement(
                        external_id=_requirement_external_id(
                            document_type=document_type,
                            attribute=attribute,
                        ),
                        id=(self._id_factory.new_id() if self._id_factory is not None else None),
                        document_type_id=document_type_id,
                        attribute_definition_id=attribute_definition_id,
                        required=item.required,
                        include_metadata_in_context_resolver=item.include_metadata_in_context_resolver,
                        missing_required_action=item.missing_required_action,
                        created_at=timestamp,
                        updated_at=timestamp,
                    ),
                )
            except ValueError as error:
                raise AttributeRequirementValidationError(message=str(error)) from error

        _raise_for_duplicate_attribute_definition_ids(duplicate_attribute_ids)
        if missing_attribute_ids:
            raise AttributeRequirementReferenceError(
                missing_attribute_ids=tuple(sorted(missing_attribute_ids)),
            )

        requirement_tuple = tuple(requirements)
        await self._repository.replace_for_document_type(
            document_type_id,
            requirement_tuple,
        )
        saved_requirements = await self._repository.list_for_document_type(
            document_type_id,
        )
        if not saved_requirements:
            saved_requirements = requirement_tuple

        return await self._build_matrix(
            document_type=document_type,
            attributes=attributes,
            requirements=saved_requirements,
            metadata_category_ids=metadata_category_ids,
        )

    async def _build_matrix(
        self,
        *,
        document_type: DocumentType,
        attributes: tuple[AttributeDefinition, ...],
        requirements: tuple[DocumentTypeAttributeRequirement, ...],
        metadata_category_ids: frozenset[UUID] | None = None,
    ) -> DocumentTypeAttributeRequirementMatrix:
        matrix = _build_matrix(
            document_type=document_type,
            attributes=attributes,
            requirements=requirements,
        )
        if metadata_category_ids is None:
            metadata_category_ids = await self._active_metadata_category_ids()
        entries: list[AttributeRequirementEntry] = []
        metadata_attribute_ids: set[UUID] = set()
        for entry in matrix.requirements:
            is_metadata = _attribute_is_active_metadata(
                entry.attribute,
                metadata_category_ids=metadata_category_ids,
            )
            if is_metadata:
                metadata_attribute_ids.add(UUID(str(entry.attribute.id)))
            entries.append(
                AttributeRequirementEntry(
                    requirement=entry.requirement,
                    attribute=entry.attribute,
                    is_metadata=is_metadata,
                )
            )
        for attribute in matrix.unassigned_attributes:
            if _attribute_is_active_metadata(
                attribute,
                metadata_category_ids=metadata_category_ids,
            ):
                metadata_attribute_ids.add(UUID(str(attribute.id)))
        return DocumentTypeAttributeRequirementMatrix(
            document_type=matrix.document_type,
            requirements=tuple(entries),
            unassigned_attributes=matrix.unassigned_attributes,
            metadata_attribute_ids=frozenset(metadata_attribute_ids),
        )

    async def _active_metadata_category_ids(self) -> frozenset[UUID]:
        categories = await self._attribute_category_repository.list()
        return frozenset(
            UUID(str(category.id))
            for category in categories
            if category.is_active and attribute_category_is_metadata(category)
        )

    async def _get_document_type(self, document_type_id: UUID | str) -> DocumentType:
        document_type = await self._document_type_repository.get_by_id(document_type_id)
        if document_type is None:
            raise DocumentTypeNotFoundError(document_type_id=document_type_id)

        return document_type


def _validated_document_type_id(document_type_id: str | UUID) -> UUID | str:
    try:
        return UUID(str(document_type_id))
    except ValueError as error:
        try:
            return normalize_document_type_external_id(str(document_type_id))
        except ValueError as external_error:
            raise DocumentTypeValidationError(message=str(external_error)) from error


def _validated_attribute_definition_id(attribute_definition_id: str | UUID) -> UUID | str:
    try:
        return UUID(str(attribute_definition_id))
    except ValueError as error:
        try:
            return normalize_attribute_external_id(str(attribute_definition_id))
        except ValueError as external_error:
            raise AttributeRequirementValidationError(message=str(external_error)) from error


def _attribute_by_reference(
    *,
    attributes_by_id: dict[UUID, AttributeDefinition],
    attributes_by_external_id: dict[str, AttributeDefinition],
    attribute_reference: UUID | str,
) -> AttributeDefinition | None:
    if isinstance(attribute_reference, UUID):
        return attributes_by_id.get(attribute_reference)

    return attributes_by_external_id.get(attribute_reference)


def _attribute_is_active_metadata(
    attribute: AttributeDefinition,
    *,
    metadata_category_ids: frozenset[UUID],
) -> bool:
    """Return whether an active attribute belongs to an active metadata category."""

    return (
        attribute.is_active
        and attribute.category_id is not None
        and UUID(str(attribute.category_id)) in metadata_category_ids
    )


def _raise_for_duplicate_attribute_definition_ids(
    duplicate_attribute_ids: set[str],
) -> None:
    if not duplicate_attribute_ids:
        return

    raise AttributeRequirementValidationError(
        message=(
            "Attribute requirement payload cannot contain duplicate attribute definition IDs."
        ),
        details={
            "duplicate_attribute_definition_ids": tuple(sorted(duplicate_attribute_ids)),
        },
    )


def _build_matrix(
    *,
    document_type: DocumentType,
    attributes: tuple[AttributeDefinition, ...],
    requirements: tuple[DocumentTypeAttributeRequirement, ...],
) -> DocumentTypeAttributeRequirementMatrix:
    attributes_by_id = {UUID(str(attribute.id)): attribute for attribute in attributes}
    missing_attribute_ids = tuple(
        sorted(
            {
                str(requirement.attribute_definition_id)
                for requirement in requirements
                if UUID(str(requirement.attribute_definition_id)) not in attributes_by_id
            },
        ),
    )
    if missing_attribute_ids:
        raise AttributeRequirementConfigurationError(
            missing_attribute_ids=missing_attribute_ids,
        )

    entries = tuple(
        sorted(
            (
                AttributeRequirementEntry(
                    requirement=requirement,
                    attribute=attributes_by_id[UUID(str(requirement.attribute_definition_id))],
                )
                for requirement in requirements
            ),
            key=lambda entry: _attribute_sort_key(entry.attribute),
        ),
    )
    assigned_attribute_ids = {
        UUID(str(entry.requirement.attribute_definition_id)) for entry in entries
    }
    unassigned_attributes = tuple(
        sorted(
            (
                attribute
                for attribute in attributes
                if UUID(str(attribute.id)) not in assigned_attribute_ids
            ),
            key=_attribute_sort_key,
        ),
    )
    return DocumentTypeAttributeRequirementMatrix(
        document_type=document_type,
        requirements=entries,
        unassigned_attributes=unassigned_attributes,
    )


def _attribute_sort_key(attribute: AttributeDefinition) -> tuple[str, str, str]:
    return (attribute.category or "", attribute.name, attribute.external_id or str(attribute.id))


def _requirement_external_id(
    *,
    document_type: DocumentType,
    attribute: AttributeDefinition,
) -> str:
    return (
        "requirement_"
        + uuid5(
            NAMESPACE_URL,
            (
                "docmind:attribute-requirement:"
                f"{document_type.external_id or document_type.id}:"
                f"{attribute.external_id or attribute.id}"
            ),
        ).hex
    )


def _attribute_assignments_version(
    requirements: tuple[DocumentTypeAttributeRequirement, ...],
) -> str:
    payload = "|".join(
        f"{item.document_type_id}:{item.id}:{item.required}:{item.include_metadata_in_context_resolver}:{item.missing_required_action}:{item.updated_at.isoformat()}"
        for item in sorted(requirements, key=lambda item: str(item.document_type_id))
    )
    return hashlib.sha256(payload.encode()).hexdigest()
