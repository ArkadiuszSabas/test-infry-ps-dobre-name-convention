"""HTTP schemas for custom dictionary endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from docmind_api.api.attributes.schemas import AttributeConstraintsRequest, AttributeDataTypeRequest
from docmind_api.application.dictionaries.commands import (
    DICTIONARY_ENTRY_LIST_DEFAULT_LIMIT,
)
from docmind_api.domain.attributes.models import AttributeDataType
from docmind_api.domain.dictionaries.models import (
    DICTIONARY_DESCRIPTION_MAX_LENGTH,
    DICTIONARY_ENTRY_LABEL_MAX_LENGTH,
    DICTIONARY_FIELD_LABEL_MAX_LENGTH,
    DICTIONARY_ID_MAX_LENGTH,
    DICTIONARY_NAME_MAX_LENGTH,
    DictionaryEntryScalar,
    DictionaryStatus,
)


class CreateDictionaryRequest(BaseModel):
    """HTTP request schema for creating a dictionary."""

    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(max_length=DICTIONARY_ID_MAX_LENGTH)
    name: str = Field(max_length=DICTIONARY_NAME_MAX_LENGTH)
    description: str | None = Field(
        default=None,
        max_length=DICTIONARY_DESCRIPTION_MAX_LENGTH,
    )


class UpdateDictionaryRequest(BaseModel):
    """HTTP request schema for editing dictionary business fields."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=DICTIONARY_NAME_MAX_LENGTH)
    description: str | None = Field(
        default=None,
        max_length=DICTIONARY_DESCRIPTION_MAX_LENGTH,
    )


class DictionarySchema(BaseModel):
    """HTTP schema for one dictionary."""

    id: UUID
    external_id: str
    name: str
    description: str | None
    status: DictionaryStatus
    schema_version: int
    entries_version: int
    created_at: datetime
    updated_at: datetime


class DictionaryEnvelope(BaseModel):
    """Standard API response envelope for one dictionary."""

    data: DictionarySchema
    meta: dict[str, str] = Field(default_factory=dict)


class DictionaryListSchema(BaseModel):
    """HTTP schema for dictionary lists."""

    dictionaries: list[DictionarySchema]


class DictionaryListMeta(BaseModel):
    """HTTP metadata for dictionary lists."""

    total_count: int


class DictionaryListEnvelope(BaseModel):
    """Standard API response envelope for dictionary lists."""

    data: DictionaryListSchema
    meta: DictionaryListMeta


class DeleteDictionarySchema(BaseModel):
    """HTTP schema for a deleted dictionary result."""

    id: UUID
    deleted: bool


class DeleteDictionaryEnvelope(BaseModel):
    """Standard API response envelope for a deleted dictionary result."""

    data: DeleteDictionarySchema
    meta: dict[str, str] = Field(default_factory=dict)


class DeleteDictionaryEntrySchema(BaseModel):
    """HTTP schema for a deleted dictionary entry result."""

    id: UUID
    deleted: bool


class DeleteDictionaryEntryEnvelope(BaseModel):
    """Standard API response envelope for a deleted dictionary entry result."""

    data: DeleteDictionaryEntrySchema
    meta: dict[str, str] = Field(default_factory=dict)


class DictionaryFieldRequest(BaseModel):
    """HTTP request schema for one dictionary field row."""

    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(max_length=DICTIONARY_ID_MAX_LENGTH)
    label: str = Field(max_length=DICTIONARY_FIELD_LABEL_MAX_LENGTH)
    data_type: AttributeDataTypeRequest = AttributeDataTypeRequest.STRING
    required: bool = False
    constraints: AttributeConstraintsRequest = Field(
        default_factory=AttributeConstraintsRequest,
    )
    normalization: dict[str, object] = Field(default_factory=dict)
    format: dict[str, object] = Field(default_factory=dict)
    is_unique: bool = False
    sort_order: int = Field(default=0, ge=0)
    status: DictionaryStatus = DictionaryStatus.ACTIVE


class SaveDictionaryFieldsRequest(BaseModel):
    """HTTP request schema for replacing dictionary field schema."""

    model_config = ConfigDict(extra="forbid")

    fields: list[DictionaryFieldRequest]


class DictionaryFieldSchema(BaseModel):
    """HTTP schema for one dictionary field."""

    id: UUID
    dictionary_id: UUID
    external_id: str
    label: str
    data_type: AttributeDataType
    required: bool
    constraints: dict[str, int | float | str]
    normalization: dict[str, object]
    format: dict[str, object]
    is_unique: bool
    sort_order: int
    status: DictionaryStatus
    created_at: datetime
    updated_at: datetime


class DictionaryFieldsPayload(BaseModel):
    """HTTP payload for dictionary field schema."""

    fields: list[DictionaryFieldSchema]


class DictionaryFieldsMeta(BaseModel):
    """HTTP metadata for dictionary field schema."""

    dictionary_id: UUID
    field_count: int


class DictionaryFieldsEnvelope(BaseModel):
    """Standard API response envelope for dictionary fields."""

    data: DictionaryFieldsPayload
    meta: DictionaryFieldsMeta


class CreateDictionaryEntryRequest(BaseModel):
    """HTTP request schema for creating a dictionary entry."""

    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(max_length=DICTIONARY_ID_MAX_LENGTH)
    label: str = Field(max_length=DICTIONARY_ENTRY_LABEL_MAX_LENGTH)
    values: dict[str, DictionaryEntryScalar]
    sort_order: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_values_object(self) -> CreateDictionaryEntryRequest:
        """Keep a clear local validation hook for entry values objects."""

        return self


class UpdateDictionaryEntryRequest(BaseModel):
    """HTTP request schema for editing a dictionary entry."""

    model_config = ConfigDict(extra="forbid")

    external_id: str | None = Field(default=None, max_length=DICTIONARY_ID_MAX_LENGTH)
    label: str | None = Field(default=None, max_length=DICTIONARY_ENTRY_LABEL_MAX_LENGTH)
    values: dict[str, DictionaryEntryScalar] | None = None
    sort_order: int | None = Field(default=None, ge=0)

    @field_validator("external_id")
    @classmethod
    def reject_explicit_null_external_id(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Dictionary entry external_id cannot be null.")
        return value


class DictionaryEntrySchema(BaseModel):
    """HTTP schema for one dictionary entry."""

    id: UUID
    dictionary_id: UUID
    external_id: str
    label: str
    values: dict[str, DictionaryEntryScalar]
    status: DictionaryStatus
    sort_order: int | None
    created_at: datetime
    updated_at: datetime


class DictionaryEntryEnvelope(BaseModel):
    """Standard API response envelope for one dictionary entry."""

    data: DictionaryEntrySchema
    meta: dict[str, str] = Field(default_factory=dict)


class DictionaryEntryListSchema(BaseModel):
    """HTTP schema for dictionary entry lists."""

    entries: list[DictionaryEntrySchema]


class DictionaryEntryListMeta(BaseModel):
    """HTTP metadata for paged dictionary entry lookup."""

    dictionary_id: UUID
    returned_count: int
    total_count: int
    limit: int = DICTIONARY_ENTRY_LIST_DEFAULT_LIMIT
    offset: int = 0
    has_more: bool


class DictionaryEntryListEnvelope(BaseModel):
    """Standard API response envelope for dictionary entry lists."""

    data: DictionaryEntryListSchema
    meta: DictionaryEntryListMeta
