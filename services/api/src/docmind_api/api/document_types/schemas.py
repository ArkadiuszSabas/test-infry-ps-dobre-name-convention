"""HTTP schemas for document type catalog endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from docmind_api.application.document_types.service import DocumentTypeListStatus
from docmind_api.domain.document_types.models import (
    DOCUMENT_TYPE_DESCRIPTION_MAX_LENGTH,
    DOCUMENT_TYPE_ID_MAX_LENGTH,
    DOCUMENT_TYPE_NAME_MAX_LENGTH,
    DocumentTypeStatus,
)
from docmind_api.domain.system_catalogs.models import SystemCatalogExtensionValueType


class DocumentTypeExtensionValueRequest(BaseModel):
    """HTTP request schema for one dynamic document type extension value."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    extension_field_id: UUID = Field(alias="extensionFieldId")
    dictionary_entry_id: UUID | None = Field(default=None, alias="dictionaryEntryId")
    text_value: str | None = Field(default=None, alias="textValue")


def _empty_extension_value_requests() -> list[DocumentTypeExtensionValueRequest]:
    return []


class CreateDocumentTypeRequest(BaseModel):
    """HTTP request schema for creating a document type."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    external_id: str | None = Field(default=None, max_length=DOCUMENT_TYPE_ID_MAX_LENGTH)
    name: str = Field(max_length=DOCUMENT_TYPE_NAME_MAX_LENGTH)
    description: str | None = Field(
        default=None,
        max_length=DOCUMENT_TYPE_DESCRIPTION_MAX_LENGTH,
    )
    extension_values: list[DocumentTypeExtensionValueRequest] = Field(
        default_factory=_empty_extension_value_requests,
        alias="extensionValues",
    )


class UpdateDocumentTypeRequest(BaseModel):
    """HTTP request schema for editing document type business fields."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    external_id: str | None = Field(default=None, max_length=DOCUMENT_TYPE_ID_MAX_LENGTH)
    name: str = Field(max_length=DOCUMENT_TYPE_NAME_MAX_LENGTH)
    description: str | None = Field(
        default=None,
        max_length=DOCUMENT_TYPE_DESCRIPTION_MAX_LENGTH,
    )
    extension_values: list[DocumentTypeExtensionValueRequest] = Field(
        default_factory=_empty_extension_value_requests,
        alias="extensionValues",
    )


class DocumentTypeExtensionValueSchema(BaseModel):
    """HTTP schema for one dynamic document type extension value."""

    model_config = ConfigDict(populate_by_name=True)

    extension_field_id: UUID = Field(alias="extensionFieldId")
    code: str
    label: str
    value_type: SystemCatalogExtensionValueType = Field(alias="valueType")
    dictionary_id: UUID | None = Field(alias="dictionaryId")
    dictionary_entry_id: UUID | None = Field(alias="dictionaryEntryId")
    text_value: str | None = Field(alias="textValue")
    display_value: str | None = Field(alias="displayValue")
    show_in_overview: bool = Field(alias="showInOverview")
    field_order: int = Field(alias="fieldOrder")


class DocumentTypeOverviewParameterSchema(BaseModel):
    """HTTP schema for one document type overview parameter."""

    code: str
    label: str
    value: str | None


class DocumentTypeSchema(BaseModel):
    """HTTP schema for a configured document type."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    external_id: str | None
    name: str
    description: str | None
    status: DocumentTypeStatus
    created_at: datetime
    updated_at: datetime
    display_label: str = Field(alias="displayLabel")
    extension_values: list[DocumentTypeExtensionValueSchema] = Field(alias="extensionValues")
    parameters: list[DocumentTypeOverviewParameterSchema]
    display_mode_id: UUID | None = Field(alias="displayModeId")


class DocumentTypeEnvelope(BaseModel):
    """Standard API response envelope for one document type."""

    data: DocumentTypeSchema
    meta: dict[str, str] = Field(default_factory=dict)


class DeleteDocumentTypeSchema(BaseModel):
    """HTTP schema for a deleted document type result."""

    id: UUID
    deleted: bool


class DeleteDocumentTypeEnvelope(BaseModel):
    """Standard API response envelope for a deleted document type."""

    data: DeleteDocumentTypeSchema
    meta: dict[str, str] = Field(default_factory=dict)


class DocumentTypeListSchema(BaseModel):
    """HTTP schema for active document type catalog results."""

    document_types: list[DocumentTypeSchema]


class DocumentTypeListMetaSchema(BaseModel):
    """HTTP metadata for document type catalog results."""

    total_count: int
    active_count: int
    inactive_count: int
    returned_count: int
    status: DocumentTypeListStatus


class DocumentTypeListEnvelope(BaseModel):
    """Standard API response envelope for document type lists."""

    data: DocumentTypeListSchema
    meta: DocumentTypeListMetaSchema
