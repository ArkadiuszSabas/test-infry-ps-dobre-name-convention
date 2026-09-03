"""HTTP schemas for document type attribute requirement endpoints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from docmind_api.domain.attribute_requirements.models import MissingRequiredAttributeAction
from docmind_api.domain.attributes.models import (
    AttributeDataType,
    AttributeStatus,
    AttributeValueSource,
)
from docmind_api.domain.document_types.models import DocumentTypeStatus


class SaveAttributeRequirementItemRequest(BaseModel):
    """HTTP request schema for one submitted attribute requirement row."""

    model_config = ConfigDict(extra="forbid")

    attribute_definition_id: UUID
    required: bool
    include_metadata_in_context_resolver: bool = False
    missing_required_action: MissingRequiredAttributeAction | None = None


class SaveAttributeRequirementsRequest(BaseModel):
    """HTTP request schema for replacing a document type's requirement matrix."""

    model_config = ConfigDict(extra="forbid")

    requirements: list[SaveAttributeRequirementItemRequest] = Field()


class AttributeRequirementDocumentTypeSchema(BaseModel):
    """Document type summary returned by matrix endpoints."""

    id: UUID
    external_id: str | None
    name: str
    status: DocumentTypeStatus


class AttributeRequirementAttributeSchema(BaseModel):
    """Attribute definition summary returned by matrix endpoints."""

    id: UUID
    external_id: str | None
    name: str
    category: str
    status: AttributeStatus
    is_metadata: bool = False


class AttributeRequirementSchema(BaseModel):
    """Configured attribute requirement row returned by matrix endpoints."""

    id: UUID
    external_id: str
    attribute: AttributeRequirementAttributeSchema
    required: bool
    include_metadata_in_context_resolver: bool
    missing_required_action: MissingRequiredAttributeAction | None
    created_at: datetime
    updated_at: datetime


class AttributeRequirementMatrixSchema(BaseModel):
    """Matrix payload for one document type."""

    document_type: AttributeRequirementDocumentTypeSchema
    requirements: list[AttributeRequirementSchema]
    unassigned_attributes: list[AttributeRequirementAttributeSchema]


class AttributeRequirementMatrixMetaSchema(BaseModel):
    """Counters for one document type matrix."""

    document_type_id: UUID
    total_attribute_count: int
    assigned_attribute_count: int
    required_attribute_count: int
    optional_attribute_count: int
    unassigned_attribute_count: int


class AttributeRequirementMatrixEnvelope(BaseModel):
    """Standard API response envelope for a document type matrix."""

    data: AttributeRequirementMatrixSchema
    meta: AttributeRequirementMatrixMetaSchema


class AttributeAssignmentSchema(BaseModel):
    """One document type's assignment state for an attribute."""

    document_type: AttributeRequirementDocumentTypeSchema
    state: Literal["required", "optional", "unassigned"]
    requirement_id: UUID | None = None
    include_metadata_in_context_resolver: bool = False
    missing_required_action: MissingRequiredAttributeAction | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AttributeAssignmentMetaSchema(BaseModel):
    total_count: int
    assigned_count: int
    unassigned_count: int
    required_count: int
    optional_count: int
    version: str


class AttributeAssignmentPayloadSchema(BaseModel):
    attribute: AttributeRequirementAttributeSchema
    assignments: list[AttributeAssignmentSchema]


class AttributeAssignmentEnvelope(BaseModel):
    data: AttributeAssignmentPayloadSchema
    meta: AttributeAssignmentMetaSchema


class SaveAttributeAssignmentItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_type_id: UUID
    required: bool
    include_metadata_in_context_resolver: bool = False
    missing_required_action: MissingRequiredAttributeAction | None = None


class SaveAttributeAssignmentsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_version: str
    assignments: list[SaveAttributeAssignmentItemRequest] = Field()


class MetadataSchemaFieldSchema(BaseModel):
    """Strongly typed metadata schema field assigned to one document type."""

    id: UUID
    external_id: str | None
    key: str
    label: str
    category: str
    data_type: AttributeDataType
    required: bool
    constraints: dict[str, int | float | str]
    allowed_values: list[str]
    value_source: AttributeValueSource
    dictionary_id: UUID | None
    status: AttributeStatus
    schema_version: int
    created_at: datetime
    updated_at: datetime


class MetadataSchemaDocumentTypeSchema(BaseModel):
    """Document type summary returned by metadata schema endpoints."""

    id: UUID
    external_id: str | None
    name: str
    status: DocumentTypeStatus


class MetadataSchemaPayloadSchema(BaseModel):
    """Metadata schema payload inherited by documents of a document type."""

    document_type: MetadataSchemaDocumentTypeSchema
    fields: list[MetadataSchemaFieldSchema]


class MetadataSchemaMetaSchema(BaseModel):
    """Counters for one document type metadata schema."""

    document_type_id: UUID
    field_count: int
    required_field_count: int
    optional_field_count: int


class MetadataSchemaEnvelope(BaseModel):
    """Standard API response envelope for a document type metadata schema."""

    data: MetadataSchemaPayloadSchema
    meta: MetadataSchemaMetaSchema
