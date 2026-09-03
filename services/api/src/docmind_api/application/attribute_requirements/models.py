"""Application data structures for attribute requirements."""

from dataclasses import dataclass
from http import HTTPStatus
from uuid import UUID

from docmind_api.domain.attribute_requirements.models import (
    DocumentTypeAttributeRequirement,
    MissingRequiredAttributeAction,
)
from docmind_api.domain.attributes.models import AttributeDefinition
from docmind_api.domain.document_types.models import DocumentType
from docmind_backend_runtime.errors import (
    ApplicationError,
    ConflictError,
    ValidationApplicationError,
)


@dataclass(frozen=True, slots=True, init=False)
class SaveAttributeRequirementItem:
    attribute_definition_id: UUID | str
    required: bool
    include_metadata_in_context_resolver: bool = False
    missing_required_action: MissingRequiredAttributeAction | None = None

    def __init__(
        self,
        *,
        required: bool,
        include_metadata_in_context_resolver: bool = False,
        missing_required_action: MissingRequiredAttributeAction | None = None,
        attribute_definition_id: UUID | str | None = None,
        attribute_id: UUID | str | None = None,
    ) -> None:
        reference = attribute_definition_id if attribute_definition_id is not None else attribute_id
        if reference is None:
            raise ValueError("Attribute definition ID is required.")
        object.__setattr__(self, "attribute_definition_id", reference)
        object.__setattr__(self, "required", required)
        object.__setattr__(
            self, "include_metadata_in_context_resolver", include_metadata_in_context_resolver
        )
        object.__setattr__(self, "missing_required_action", missing_required_action)

    @property
    def attribute_id(self) -> UUID | str:
        return self.attribute_definition_id


@dataclass(frozen=True, slots=True)
class SaveDocumentTypeAttributeRequirementsCommand:
    document_type_id: UUID | str
    requirements: tuple[SaveAttributeRequirementItem, ...]


@dataclass(frozen=True, slots=True)
class SaveAttributeDocumentTypeAssignmentItem:
    document_type_id: UUID
    required: bool
    include_metadata_in_context_resolver: bool
    missing_required_action: MissingRequiredAttributeAction | None


@dataclass(frozen=True, slots=True)
class SaveAttributeDocumentTypeAssignmentsCommand:
    attribute_id: UUID
    base_version: str
    assignments: tuple[SaveAttributeDocumentTypeAssignmentItem, ...]


@dataclass(frozen=True, slots=True)
class AttributeRequirementEntry:
    requirement: DocumentTypeAttributeRequirement
    attribute: AttributeDefinition
    is_metadata: bool = False


@dataclass(frozen=True, slots=True)
class DocumentTypeAttributeRequirementMatrix:
    document_type: DocumentType
    requirements: tuple[AttributeRequirementEntry, ...]
    unassigned_attributes: tuple[AttributeDefinition, ...]
    metadata_attribute_ids: frozenset[UUID] = frozenset()

    @property
    def total_attribute_count(self) -> int:
        return self.assigned_attribute_count + self.unassigned_attribute_count

    @property
    def assigned_attribute_count(self) -> int:
        return len(self.requirements)

    @property
    def required_attribute_count(self) -> int:
        return sum(1 for entry in self.requirements if entry.requirement.required)

    @property
    def optional_attribute_count(self) -> int:
        return self.assigned_attribute_count - self.required_attribute_count

    @property
    def unassigned_attribute_count(self) -> int:
        return len(self.unassigned_attributes)


@dataclass(frozen=True, slots=True)
class DocumentTypeMetadataSchema:
    document_type: DocumentType
    fields: tuple[AttributeRequirementEntry, ...]

    @property
    def field_count(self) -> int:
        return len(self.fields)

    @property
    def required_field_count(self) -> int:
        return sum(1 for entry in self.fields if entry.requirement.required)

    @property
    def optional_field_count(self) -> int:
        return self.field_count - self.required_field_count


class AttributeRequirementValidationError(ValidationApplicationError):
    def __init__(self, *, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(
            code="ATTRIBUTE_REQUIREMENT_VALIDATION_ERROR", message=message, details=details
        )


class AttributeRequirementReferenceError(ValidationApplicationError):
    def __init__(self, *, missing_attribute_ids: tuple[str, ...]) -> None:
        super().__init__(
            code="ATTRIBUTE_REQUIREMENT_REFERENCE_ERROR",
            message="Attribute requirement configuration references unknown attributes.",
            details={"missing_attribute_ids": missing_attribute_ids},
        )


class AttributeRequirementConfigurationError(ApplicationError):
    def __init__(self, *, missing_attribute_ids: tuple[str, ...]) -> None:
        super().__init__(
            code="ATTRIBUTE_REQUIREMENT_CONFIGURATION_ERROR",
            message="Attribute requirement configuration is inconsistent.",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details={"missing_attribute_ids": missing_attribute_ids},
        )


class AttributeAssignmentVersionConflictError(ConflictError):
    def __init__(
        self,
        *,
        current_version: str,
        current_assignments: tuple[dict[str, object], ...],
    ) -> None:
        super().__init__(
            code="ATTRIBUTE_ASSIGNMENT_VERSION_CONFLICT",
            message="Attribute assignments changed while they were being edited.",
            details={
                "current_version": current_version,
                "current_assignments": current_assignments,
            },
        )
