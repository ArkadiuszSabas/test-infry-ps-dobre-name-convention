"""Worker connector extension metadata service."""

from dataclasses import dataclass

from docmind_core.connectors import (
    ConnectorMigrationBundleDescriptor,
    ConnectorWorkerHookDescriptor,
    ProfileManifest,
)


@dataclass(frozen=True, slots=True)
class WorkerConnectorExtensionRegistry:
    """Worker connector extension descriptors selected by the profile manifest."""

    profile_id: str
    worker_hooks: tuple[ConnectorWorkerHookDescriptor, ...]
    migration_bundles: tuple[ConnectorMigrationBundleDescriptor, ...]


class WorkerConnectorExtensionService:
    """Read worker connector hook metadata from the generated manifest."""

    def __init__(self, *, manifest: ProfileManifest) -> None:
        self._manifest = manifest

    async def get_registry(self) -> WorkerConnectorExtensionRegistry:
        """Return worker hook descriptors selected by the current profile."""

        return WorkerConnectorExtensionRegistry(
            profile_id=self._manifest.profile_id,
            worker_hooks=self._manifest.worker_hooks,
            migration_bundles=self._manifest.migration_bundles,
        )
