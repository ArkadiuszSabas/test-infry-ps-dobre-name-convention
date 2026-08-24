"""HTTP response mappers for the capability registry."""

from docmind_api.api.capabilities.schemas import (
    CapabilityRegistryEnvelope,
    CapabilityRegistryMetaSchema,
    CapabilityRegistrySchema,
    CapabilitySchema,
    ConnectorInstanceSchema,
    SafeMetadataSchema,
    UiExtensionSchema,
)
from docmind_api.application.capabilities.service import CapabilityRegistry
from docmind_core.connectors import (
    ConnectorCapabilityDescriptor,
    ConnectorInstanceDescriptor,
    ConnectorUiExtensionDescriptor,
    SafeMetadata,
)


def to_capability_registry_envelope(
    registry: CapabilityRegistry,
) -> CapabilityRegistryEnvelope:
    """Map a capability registry read model to an API envelope."""

    return CapabilityRegistryEnvelope(
        data=CapabilityRegistrySchema(
            profile_id=registry.profile_id,
            capabilities=[to_capability_schema(capability) for capability in registry.capabilities],
            connector_instances=[
                to_connector_instance_schema(instance) for instance in registry.connector_instances
            ],
            ui_extensions=[
                to_ui_extension_schema(ui_extension) for ui_extension in registry.ui_extensions
            ],
        ),
        meta=CapabilityRegistryMetaSchema(
            capability_count=len(registry.capabilities),
            connector_instance_count=len(registry.connector_instances),
            ui_extension_count=len(registry.ui_extensions),
        ),
    )


def to_capability_schema(capability: ConnectorCapabilityDescriptor) -> CapabilitySchema:
    """Map a capability descriptor to its HTTP schema."""

    return CapabilitySchema(
        id=capability.id,
        module_id=capability.module_id,
        kind=capability.kind.value,
        status=capability.status.value,
        visibility=capability.visibility.value,
        contract_version=capability.contract_version,
        ui_surfaces=list(capability.ui_surfaces),
        required_permissions=list(capability.required_permissions),
        safe_metadata=to_safe_metadata_schema(capability.safe_metadata),
    )


def to_connector_instance_schema(
    instance: ConnectorInstanceDescriptor,
) -> ConnectorInstanceSchema:
    """Map a connector instance descriptor to its HTTP schema."""

    return ConnectorInstanceSchema(
        connector_instance_id=instance.connector_instance_id,
        capability_id=instance.capability_id,
        module_id=instance.module_id,
        profile_id=instance.profile_id,
        status=instance.status.value,
        visibility=instance.visibility.value,
        health=dict(instance.health),
        safe_metadata=to_safe_metadata_schema(instance.safe_metadata),
    )


def to_ui_extension_schema(ui_extension: ConnectorUiExtensionDescriptor) -> UiExtensionSchema:
    """Map a UI extension descriptor to its HTTP schema."""

    return UiExtensionSchema(
        id=ui_extension.id,
        module_id=ui_extension.module_id,
        capability_id=ui_extension.capability_id,
        connector_folder=ui_extension.connector_folder,
        slot=ui_extension.slot,
        module_path=ui_extension.module_path,
        required_permissions=list(ui_extension.required_permissions),
        required_instance_id=ui_extension.required_instance_id,
        safe_metadata=to_safe_metadata_schema(ui_extension.safe_metadata),
    )


def to_safe_metadata_schema(metadata: SafeMetadata) -> SafeMetadataSchema:
    """Map safe metadata to its HTTP schema."""

    return SafeMetadataSchema(
        label=metadata.label,
        description=metadata.description,
        extra=dict(metadata.extra),
    )
