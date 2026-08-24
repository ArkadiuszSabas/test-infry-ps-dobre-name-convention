"""Capability registry application service."""

from dataclasses import dataclass

from docmind_core.connectors import (
    ConnectorCapabilityDescriptor,
    ConnectorInstanceDescriptor,
    ConnectorUiExtensionDescriptor,
    ProfileManifest,
)


@dataclass(frozen=True, slots=True)
class CapabilityRegistry:
    """Safe capability registry payload for API/UI clients."""

    profile_id: str
    capabilities: tuple[ConnectorCapabilityDescriptor, ...]
    connector_instances: tuple[ConnectorInstanceDescriptor, ...]
    ui_extensions: tuple[ConnectorUiExtensionDescriptor, ...]


class CapabilityRegistryService:
    """Read-only capability registry backed by the generated connector manifest."""

    def __init__(self, *, manifest: ProfileManifest) -> None:
        self._manifest = manifest

    async def get_registry(self) -> CapabilityRegistry:
        """Return the safe capability registry for the current profile."""

        return CapabilityRegistry(
            profile_id=self._manifest.profile_id,
            capabilities=self._manifest.capabilities,
            connector_instances=self._manifest.connector_instances,
            ui_extensions=self._manifest.ui_extensions,
        )
