"""HTTP schemas for attribute definition catalog endpoints."""

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Self, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from docmind_api.domain.attributes.models import (
    ATTRIBUTE_CATEGORY_MAX_LENGTH,
    ATTRIBUTE_COMMENT_MAX_LENGTH,
    ATTRIBUTE_CONSTRAINT_PATTERN_MAX_LENGTH,
    ATTRIBUTE_ID_MAX_LENGTH,
    ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH,
    ATTRIBUTE_NAME_MAX_LENGTH,
    AttributeDataType,
    AttributeSource,
    AttributeStatus,
    AttributeValueSource,
    normalize_attribute_llm_context,
)


class AttributeDataTypeRequest(StrEnum):
    """Public metadata field data types accepted by write requests."""

    STRING = "string"
    IDENTIFIER = "identifier"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"


class AttributeConstraintsRequest(BaseModel):
    """HTTP request schema for metadata field validation constraints."""

    model_config = ConfigDict(extra="forbid")

    min_length: int | None = Field(default=None, ge=0)
    max_length: int | None = Field(default=None, ge=0)
    pattern: str | None = Field(
        default=None,
        max_length=ATTRIBUTE_CONSTRAINT_PATTERN_MAX_LENGTH,
    )
    min_value: float | None = None
    max_value: float | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_coerced_constraint_values(cls, values: object) -> object:
        """Reject invalid JSON types before Pydantic can coerce them."""

        if not isinstance(values, Mapping):
            return values

        constraint_values = cast(Mapping[str, object], values)
        for field_name in ("min_length", "max_length"):
            if field_name in constraint_values:
                _validate_length_constraint_type(constraint_values[field_name])

        for field_name in ("min_value", "max_value"):
            if field_name in constraint_values:
                _validate_numeric_constraint_type(constraint_values[field_name])

        return constraint_values


def _validate_length_constraint_type(value: object) -> None:
    if value is None:
        return
    if type(value) is not int:
        raise ValueError("Length constraints must be integers.")


def _validate_numeric_constraint_type(value: object) -> None:
    if value is None:
        return
    if type(value) not in (int, float):
        raise ValueError("Value constraints must be numbers.")


class CreateAttributeDefinitionRequest(BaseModel):
    """HTTP request schema for creating an attribute definition."""

    model_config = ConfigDict(extra="forbid")

    external_id: str | None = Field(default=None, max_length=ATTRIBUTE_ID_MAX_LENGTH)
    name: str = Field(max_length=ATTRIBUTE_NAME_MAX_LENGTH)
    source: AttributeSource
    category_id: UUID | None = None
    data_type: AttributeDataTypeRequest = AttributeDataTypeRequest.STRING
    constraints: AttributeConstraintsRequest = Field(
        default_factory=AttributeConstraintsRequest,
    )
    allowed_values: list[str] = Field(default_factory=list)
    value_source: AttributeValueSource = AttributeValueSource.FREE_TEXT
    dictionary_id: UUID | None = None
    comment: str | None = Field(default=None, max_length=ATTRIBUTE_COMMENT_MAX_LENGTH)
    llm_context: str | None = Field(
        default=None,
        max_length=ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH,
    )

    @field_validator("llm_context", mode="before")
    @classmethod
    def validate_llm_context(cls, value: object) -> object:
        """Normalize blank guidance and reject unsafe control characters."""

        if value is None or isinstance(value, str):
            return normalize_attribute_llm_context(value)
        return value


class UpdateAttributeDefinitionRequest(BaseModel):
    """HTTP request schema for editing attribute definition business fields."""

    model_config = ConfigDict(extra="forbid")

    external_id: str | None = Field(default=None, max_length=ATTRIBUTE_ID_MAX_LENGTH)
    name: str | None = Field(default=None, max_length=ATTRIBUTE_NAME_MAX_LENGTH)
    source: AttributeSource | None = None
    category_id: UUID | None = None
    data_type: AttributeDataTypeRequest | None = None
    constraints: AttributeConstraintsRequest | None = None
    allowed_values: list[str] | None = None
    value_source: AttributeValueSource | None = None
    dictionary_id: UUID | None = None
    comment: str | None = Field(default=None, max_length=ATTRIBUTE_COMMENT_MAX_LENGTH)
    llm_context: str | None = Field(
        default=None,
        max_length=ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH,
    )

    @field_validator("llm_context", mode="before")
    @classmethod
    def validate_llm_context(cls, value: object) -> object:
        """Normalize blank guidance and reject unsafe control characters."""

        if value is None or isinstance(value, str):
            return normalize_attribute_llm_context(value)
        return value

    @model_validator(mode="after")
    def reject_explicit_null_source(self) -> Self:
        """Reject explicit null for the non-nullable source field."""

        if "source" in self.model_fields_set and self.source is None:
            raise ValueError("Attribute source cannot be null.")
        if "data_type" in self.model_fields_set and self.data_type is None:
            raise ValueError("Attribute data type cannot be null.")
        if "value_source" in self.model_fields_set and self.value_source is None:
            raise ValueError("Attribute value source cannot be null.")

        return self


class CreateAttributeCategoryRequest(BaseModel):
    """HTTP request schema for creating a system attribute category."""

    model_config = ConfigDict(extra="forbid")

    external_id: str | None = Field(default=None, max_length=ATTRIBUTE_ID_MAX_LENGTH)
    label: str = Field(max_length=ATTRIBUTE_CATEGORY_MAX_LENGTH)
    flags: dict[str, bool] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def reject_coerced_flag_values(cls, values: object) -> object:
        """Reject invalid flag types before Pydantic can coerce them."""

        _validate_category_flags(values)
        return values


class UpdateAttributeCategoryRequest(BaseModel):
    """HTTP request schema for editing a system attribute category."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=ATTRIBUTE_CATEGORY_MAX_LENGTH)
    flags: dict[str, bool] | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_coerced_flag_values(cls, values: object) -> object:
        """Reject invalid flag types before Pydantic can coerce them."""

        _validate_category_flags(values)
        return values


def _validate_category_flags(values: object) -> None:
    if not isinstance(values, Mapping):
        return
    payload = cast(Mapping[str, object], values)
    flags = payload.get("flags")
    if flags is None:
        return
    if not isinstance(flags, Mapping):
        raise ValueError("Attribute category flags must be an object.")
    flag_values = cast(Mapping[str, object], flags)
    for flag_value in flag_values.values():
        if type(flag_value) is not bool:
            raise ValueError("Attribute category flag values must be booleans.")


class AttributeDefinitionSchema(BaseModel):
    """HTTP schema for a configured attribute definition."""

    id: UUID
    external_id: str | None
    name: str
    category: str
    category_id: UUID | None
    data_type: AttributeDataType
    constraints: dict[str, int | float | str]
    allowed_values: list[str]
    value_source: AttributeValueSource
    dictionary_id: UUID | None
    source: AttributeSource
    comment: str | None
    llm_context: str | None
    status: AttributeStatus
    schema_version: int
    created_at: datetime
    updated_at: datetime


class AttributeDefinitionEnvelope(BaseModel):
    """Standard API response envelope for one attribute definition."""

    data: AttributeDefinitionSchema
    meta: dict[str, str] = Field(default_factory=dict)


class DeleteAttributeDefinitionSchema(BaseModel):
    """HTTP schema for a deleted attribute definition result."""

    id: UUID
    deleted: bool


class DeleteAttributeDefinitionEnvelope(BaseModel):
    """Standard API response envelope for a deleted attribute definition."""

    data: DeleteAttributeDefinitionSchema
    meta: dict[str, str] = Field(default_factory=dict)


class DeleteAttributeCategorySchema(BaseModel):
    """HTTP schema for a deleted attribute category result."""

    id: UUID
    deleted: bool


class DeleteAttributeCategoryEnvelope(BaseModel):
    """Standard API response envelope for a deleted attribute category."""

    data: DeleteAttributeCategorySchema
    meta: dict[str, str] = Field(default_factory=dict)


class AttributeDefinitionListSchema(BaseModel):
    """HTTP schema for attribute definition catalog results."""

    attributes: list[AttributeDefinitionSchema]


class AttributeCategoryCountSchema(BaseModel):
    """HTTP schema for one category counter."""

    category: str
    count: int


class AttributeDefinitionListMeta(BaseModel):
    """HTTP metadata for attribute definition catalog lists."""

    total_count: int
    category_counts: list[AttributeCategoryCountSchema]


class AttributeDefinitionListEnvelope(BaseModel):
    """Standard API response envelope for attribute definition lists."""

    data: AttributeDefinitionListSchema
    meta: AttributeDefinitionListMeta


class AttributeCategorySchema(BaseModel):
    """HTTP schema for one system attribute category."""

    id: UUID
    external_id: str
    label: str
    flags: dict[str, bool]
    status: AttributeStatus
    created_at: datetime
    updated_at: datetime


class AttributeCategoryEnvelope(BaseModel):
    """Standard API response envelope for one attribute category."""

    data: AttributeCategorySchema
    meta: dict[str, str] = Field(default_factory=dict)


class AttributeCategoryListSchema(BaseModel):
    """HTTP schema for the system attribute category catalog."""

    categories: list[AttributeCategorySchema]


class AttributeCategoryListMeta(BaseModel):
    """HTTP metadata for system attribute category lists."""

    total_count: int
    active_count: int
    inactive_count: int
    returned_count: int
    status: str


class AttributeCategoryListEnvelope(BaseModel):
    """Standard API response envelope for attribute category lists."""

    data: AttributeCategoryListSchema
    meta: AttributeCategoryListMeta
