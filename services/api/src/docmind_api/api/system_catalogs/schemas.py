"""HTTP schemas for system catalog endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from docmind_api.domain.system_catalogs.models import (
    SYSTEM_CATALOG_CODE_MAX_LENGTH,
    SYSTEM_CATALOG_KEY_MAX_LENGTH,
    SYSTEM_CATALOG_LABEL_MAX_LENGTH,
    SYSTEM_CATALOG_SEPARATOR_MAX_LENGTH,
    SystemCatalogDisplayPartSourceType,
    SystemCatalogExtensionValueType,
)


class SaveSystemCatalogExtensionFieldRequest(BaseModel):
    """HTTP request schema for one system catalog extension field."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: UUID | None = None
    code: str = Field(max_length=SYSTEM_CATALOG_CODE_MAX_LENGTH)
    label: str = Field(max_length=SYSTEM_CATALOG_LABEL_MAX_LENGTH)
    value_type: SystemCatalogExtensionValueType = Field(alias="valueType")
    dictionary_id: UUID | None = Field(default=None, alias="dictionaryId")
    mapped_attribute_definition_id: UUID | None = Field(
        default=None,
        alias="mappedAttributeDefinitionId",
    )
    is_required: bool = Field(default=False, alias="isRequired")
    show_in_overview: bool = Field(default=False, alias="showInOverview")
    field_order: int = Field(default=0, ge=0, alias="fieldOrder")
    is_active: bool = Field(default=True, alias="isActive")


class SaveSystemCatalogDisplayModePartRequest(BaseModel):
    """HTTP request schema for one display mode part."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: UUID | None = None
    part_order: int = Field(ge=0, alias="partOrder")
    source_type: SystemCatalogDisplayPartSourceType = Field(alias="sourceType")
    extension_field_id: UUID | None = Field(default=None, alias="extensionFieldId")
    extension_field_code: str | None = Field(
        default=None,
        max_length=SYSTEM_CATALOG_CODE_MAX_LENGTH,
        alias="extensionFieldCode",
    )
    separator_before: str | None = Field(
        default=None,
        max_length=SYSTEM_CATALOG_SEPARATOR_MAX_LENGTH,
        alias="separatorBefore",
    )


class SaveSystemCatalogDisplayModeRequest(BaseModel):
    """HTTP request schema for one display mode."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: UUID | None = None
    name: str = Field(max_length=SYSTEM_CATALOG_LABEL_MAX_LENGTH)
    is_default: bool = Field(default=False, alias="isDefault")
    is_active: bool = Field(default=True, alias="isActive")
    parts: list[SaveSystemCatalogDisplayModePartRequest]


class SaveSystemCatalogDefinitionRequest(BaseModel):
    """HTTP request schema for replacing a system catalog definition."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    fields: list[SaveSystemCatalogExtensionFieldRequest]
    display_modes: list[SaveSystemCatalogDisplayModeRequest] = Field(alias="displayModes")


class SystemCatalogExtensionFieldSchema(BaseModel):
    """HTTP schema for one system catalog extension field."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    system_catalog_key: str = Field(alias="systemCatalogKey")
    code: str
    label: str
    value_type: SystemCatalogExtensionValueType = Field(alias="valueType")
    dictionary_id: UUID | None = Field(alias="dictionaryId")
    mapped_attribute_definition_id: UUID | None = Field(alias="mappedAttributeDefinitionId")
    is_required: bool = Field(alias="isRequired")
    show_in_overview: bool = Field(alias="showInOverview")
    field_order: int = Field(alias="fieldOrder")
    is_active: bool = Field(alias="isActive")
    created_at: datetime
    updated_at: datetime


class SystemCatalogDisplayModePartSchema(BaseModel):
    """HTTP schema for one display mode part."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    display_mode_id: UUID = Field(alias="displayModeId")
    part_order: int = Field(alias="partOrder")
    source_type: SystemCatalogDisplayPartSourceType = Field(alias="sourceType")
    extension_field_id: UUID | None = Field(alias="extensionFieldId")
    separator_before: str | None = Field(alias="separatorBefore")


class SystemCatalogDisplayModeSchema(BaseModel):
    """HTTP schema for one display mode."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    system_catalog_key: str = Field(alias="systemCatalogKey")
    name: str
    is_default: bool = Field(alias="isDefault")
    is_active: bool = Field(alias="isActive")
    created_at: datetime
    updated_at: datetime
    parts: list[SystemCatalogDisplayModePartSchema]


class SystemCatalogDefinitionPayload(BaseModel):
    """HTTP payload for a system catalog definition."""

    model_config = ConfigDict(populate_by_name=True)

    system_catalog_key: str = Field(
        max_length=SYSTEM_CATALOG_KEY_MAX_LENGTH,
        alias="systemCatalogKey",
    )
    fields: list[SystemCatalogExtensionFieldSchema]
    display_modes: list[SystemCatalogDisplayModeSchema] = Field(alias="displayModes")


class SystemCatalogDefinitionEnvelope(BaseModel):
    """Standard API response envelope for system catalog definitions."""

    data: SystemCatalogDefinitionPayload
    meta: dict[str, str] = Field(default_factory=dict)


class SystemCatalogOptionParameterSchema(BaseModel):
    """HTTP schema for a dropdown option parameter."""

    code: str
    label: str
    value: str | None


class SystemCatalogOptionExtensionValueSchema(BaseModel):
    """HTTP schema for values used to compose dropdown display labels."""

    model_config = ConfigDict(populate_by_name=True)

    extension_field_id: UUID = Field(alias="extensionFieldId")
    display_value: str | None = Field(alias="displayValue")
    text_value: str | None = Field(alias="textValue")


class SystemCatalogOptionSchema(BaseModel):
    """HTTP schema for one unified system catalog option."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    label: str
    name: str
    extension_values: list[SystemCatalogOptionExtensionValueSchema] = Field(
        alias="extensionValues",
    )
    parameters: list[SystemCatalogOptionParameterSchema]
    display_mode_id: UUID | None = Field(alias="displayModeId")


class SystemCatalogOptionsPayload(BaseModel):
    """HTTP payload for system catalog options."""

    definition: SystemCatalogDefinitionPayload
    options: list[SystemCatalogOptionSchema]


class SystemCatalogOptionsMeta(BaseModel):
    """HTTP metadata for system catalog options."""

    model_config = ConfigDict(populate_by_name=True)

    system_catalog_key: str = Field(alias="systemCatalogKey")
    returned_count: int = Field(alias="returnedCount")


class SystemCatalogOptionsEnvelope(BaseModel):
    """Standard API response envelope for system catalog options."""

    data: SystemCatalogOptionsPayload
    meta: SystemCatalogOptionsMeta
