"""Capability registry application service."""

from dataclasses import dataclass
from enum import StrEnum

from docmind_api.application.listing import ListPage, ListRequest, process_bounded_list
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


class ConnectorInstanceSortField(StrEnum):
    """Safe sort keys for connector instance administration."""

    INSTANCE_ID = "instance_id"
    LABEL = "label"
    STATUS = "status"


@dataclass(frozen=True, slots=True)
class ListConnectorInstancesQuery:
    """Typed connector-instance list criteria."""

    request: ListRequest[ConnectorInstanceSortField]
    configurable_only: bool = True


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

    async def list_connector_instances(
        self,
        query: ListConnectorInstancesQuery,
    ) -> ListPage[ConnectorInstanceDescriptor]:
        """Filter and page the bounded manifest-owned connector catalog."""

        instances = (
            instance
            for instance in self._manifest.connector_instances
            if not query.configurable_only or instance.module_id is not None
        )
        return process_bounded_list(
            instances,
            request=query.request,
            search_values=lambda instance: (
                instance.connector_instance_id,
                instance.status.value,
                instance.safe_metadata.label,
                instance.safe_metadata.description,
            ),
            sort_value=lambda instance, field: (
                instance.connector_instance_id
                if field is ConnectorInstanceSortField.INSTANCE_ID
                else instance.status.value
                if field is ConnectorInstanceSortField.STATUS
                else instance.safe_metadata.label
            ),
            identity=lambda instance: instance.connector_instance_id,
        )
