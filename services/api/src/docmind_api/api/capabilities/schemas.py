"""HTTP schemas for the capability registry."""

from pydantic import BaseModel, Field


class SafeMetadataSchema(BaseModel):
    """Display-safe metadata exposed to API/UI clients."""

    label: str
    description: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)


class CapabilitySchema(BaseModel):
    """Safe capability type metadata."""

    id: str
    module_id: str | None = None
    kind: str
    status: str
    visibility: str
    contract_version: int
    ui_surfaces: list[str]
    required_permissions: list[str]
    safe_metadata: SafeMetadataSchema


class ConnectorInstanceSchema(BaseModel):
    """Safe configured connector instance metadata."""

    connector_instance_id: str
    capability_id: str
    module_id: str | None = None
    profile_id: str | None = None
    status: str
    visibility: str
    health: dict[str, str]
    safe_metadata: SafeMetadataSchema


class UiExtensionSchema(BaseModel):
    """Safe UI extension descriptor selected by the profile manifest."""

    id: str
    module_id: str
    capability_id: str
    connector_folder: str
    slot: str
    module_path: str
    required_permissions: list[str]
    required_instance_id: str | None = None
    safe_metadata: SafeMetadataSchema


class CapabilityRegistrySchema(BaseModel):
    """Capability registry payload."""

    profile_id: str
    capabilities: list[CapabilitySchema]
    connector_instances: list[ConnectorInstanceSchema]
    ui_extensions: list[UiExtensionSchema]


class CapabilityRegistryMetaSchema(BaseModel):
    """Capability registry response metadata."""

    capability_count: int
    connector_instance_count: int
    ui_extension_count: int


class CapabilityRegistryEnvelope(BaseModel):
    """Standard API response envelope for capabilities."""

    data: CapabilityRegistrySchema
    meta: CapabilityRegistryMetaSchema
