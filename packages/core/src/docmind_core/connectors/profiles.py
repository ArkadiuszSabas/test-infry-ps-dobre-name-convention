"""Deployment profile validation and manifest generation."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from importlib import import_module
from pathlib import Path
from types import MappingProxyType
from typing import cast

from docmind_core.connectors.contracts import (
    BUILTIN_MANUAL_UPLOAD_CAPABILITY_ID,
    ConnectorApiRouteDescriptor,
    ConnectorCapabilityDescriptor,
    ConnectorCapabilityKind,
    ConnectorInstanceDescriptor,
    ConnectorMigrationBundleDescriptor,
    ConnectorModuleDescriptor,
    ConnectorStatus,
    ConnectorUiExtensionDescriptor,
    ConnectorVisibility,
    ConnectorWorkerHookDescriptor,
    SafeMetadata,
    manual_upload_capability,
    manual_upload_instance,
)

SUPPORTED_PROFILE_SCHEMA_VERSION = 1
_METADATA_BOOLEAN_MAKES_ALL_OPTIONAL = "metadata_boolean_makes_all_optional"
_PROFILE_ID_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_WINDOWS_RESERVED_PROFILE_IDS = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


class ProfileValidationError(ValueError):
    """Raised when a deployment profile or generated manifest is invalid."""


class SourcePackageDeliveryTarget(StrEnum):
    """Allowed source-package delivery destinations."""

    INTERNAL = "internal"
    CUSTOMER = "customer"


@dataclass(frozen=True, slots=True)
class InstalledModuleProfileEntry:
    """Profile entry describing an installed optional connector module."""

    module_id: str
    connector_folder: str
    import_path: str
    api_router_entrypoint: str | None = None
    approved_document_handler_entrypoint: str | None = None
    document_deletion_handler_entrypoint: str | None = None
    api_route_prefixes: tuple[str, ...] = ()
    worker_hook_ids: tuple[str, ...] = ()
    migration_bundle_ids: tuple[str, ...] = ()
    ui_extension_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourcePackageProfile:
    """Profile source snapshot allowlist and forbidden scan terms."""

    delivery_target: SourcePackageDeliveryTarget = SourcePackageDeliveryTarget.INTERNAL
    include_paths: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()
    allow_core_only_delivery: bool = False
    overlay_path: str | None = None


@dataclass(frozen=True, slots=True)
class EffectiveAttributeRequirementsPolicyProfile:
    """Profile-selected rule for deriving runtime attribute requiredness."""

    trigger_metadata_key: str


@dataclass(frozen=True, slots=True)
class RuntimePoliciesProfile:
    """Runtime policies selected for one deployment profile."""

    effective_attribute_requirements: EffectiveAttributeRequirementsPolicyProfile | None = None


@dataclass(frozen=True, slots=True)
class DeploymentProfile:
    """Versioned deployment profile loaded from `deployments/<profile>/profile.yml`."""

    schema_version: int
    profile_id: str
    display_name: str
    installed_modules: tuple[InstalledModuleProfileEntry, ...] = ()
    enabled_capabilities: tuple[ConnectorCapabilityDescriptor, ...] = ()
    connector_instances: tuple[ConnectorInstanceDescriptor, ...] = ()
    ui_extensions: tuple[ConnectorUiExtensionDescriptor, ...] = ()
    migration_bundles: tuple[ConnectorMigrationBundleDescriptor, ...] = ()
    source_package: SourcePackageProfile = field(default_factory=SourcePackageProfile)
    runtime_policies: RuntimePoliciesProfile = field(default_factory=RuntimePoliciesProfile)

    def __post_init__(self) -> None:
        if self.schema_version != SUPPORTED_PROFILE_SCHEMA_VERSION:
            raise ProfileValidationError(
                f"Unsupported deployment profile schema version: {self.schema_version}.",
            )
        if (
            _PROFILE_ID_PATTERN.fullmatch(self.profile_id) is None
            or self.profile_id in _WINDOWS_RESERVED_PROFILE_IDS
        ):
            raise ProfileValidationError(
                "Deployment profile_id must be a portable identifier of at most 63 characters, "
                "using lowercase letters, digits, and interior hyphens, and must not be a "
                "reserved Windows device name.",
            )


@dataclass(frozen=True, slots=True)
class ProfileManifest:
    """Deterministic runtime manifest generated from a deployment profile."""

    schema_version: int
    profile_id: str
    installed_modules: tuple[ConnectorModuleDescriptor, ...]
    capabilities: tuple[ConnectorCapabilityDescriptor, ...]
    connector_instances: tuple[ConnectorInstanceDescriptor, ...]
    api_routes: tuple[ConnectorApiRouteDescriptor, ...]
    worker_hooks: tuple[ConnectorWorkerHookDescriptor, ...]
    ui_extensions: tuple[ConnectorUiExtensionDescriptor, ...]
    migration_bundles: tuple[ConnectorMigrationBundleDescriptor, ...]
    source_package: SourcePackageProfile
    runtime_policies: RuntimePoliciesProfile


ConnectorModuleLoader = Callable[[str], ConnectorModuleDescriptor]
YamlSafeLoad = Callable[[str], object]


def load_deployment_profile(path: Path) -> DeploymentProfile:
    """Load a deployment profile from a YAML file."""

    payload = _load_yaml_mapping(path)
    return deployment_profile_from_mapping(payload)


def deployment_profile_to_mapping(
    profile: DeploymentProfile,
    *,
    include_source_package: bool = True,
) -> Mapping[str, object]:
    """Return a YAML-safe deployment profile mapping."""

    payload: dict[str, object] = {
        "schema_version": profile.schema_version,
        "profile_id": profile.profile_id,
        "display_name": profile.display_name,
        "installed_modules": [
            {
                "module_id": item.module_id,
                "connector_folder": item.connector_folder,
                "import_path": item.import_path,
                "api_router_entrypoint": item.api_router_entrypoint,
                "approved_document_handler_entrypoint": (item.approved_document_handler_entrypoint),
                "document_deletion_handler_entrypoint": (item.document_deletion_handler_entrypoint),
                "api_route_prefixes": list(item.api_route_prefixes),
                "worker_hook_ids": list(item.worker_hook_ids),
                "migration_bundle_ids": list(item.migration_bundle_ids),
                "ui_extension_ids": list(item.ui_extension_ids),
            }
            for item in profile.installed_modules
        ],
        "enabled_capabilities": [
            _capability_to_mapping(capability) for capability in profile.enabled_capabilities
        ],
        "connector_instances": [
            _instance_to_mapping(instance) for instance in profile.connector_instances
        ],
        "ui_extensions": [
            _ui_extension_to_mapping(extension) for extension in profile.ui_extensions
        ],
        "migration_bundles": [
            {
                "id": bundle.id,
                "module_id": bundle.module_id,
                "path": bundle.path,
            }
            for bundle in profile.migration_bundles
        ],
        "runtime_policies": _runtime_policies_to_mapping(profile.runtime_policies),
    }
    if include_source_package:
        payload["source_package"] = {
            "delivery_target": profile.source_package.delivery_target.value,
            "include_paths": list(profile.source_package.include_paths),
            "forbidden_terms": list(profile.source_package.forbidden_terms),
            "allow_core_only_delivery": profile.source_package.allow_core_only_delivery,
            "overlay_path": profile.source_package.overlay_path,
        }
    return payload


def deployment_profile_from_mapping(payload: Mapping[str, object]) -> DeploymentProfile:
    """Parse a deployment profile mapping into typed contracts."""

    schema_version = _required_int(payload, "schema_version")
    profile_id = _required_str(payload, "profile_id")
    display_name = _required_str(payload, "display_name")
    installed_modules = tuple(
        _installed_module_from_mapping(item)
        for item in _mapping_items(payload, "installed_modules")
    )
    enabled_capabilities = tuple(
        _capability_from_mapping(item) for item in _mapping_items(payload, "enabled_capabilities")
    )
    connector_instances = tuple(
        _instance_from_mapping(item, profile_id=profile_id)
        for item in _mapping_items(payload, "connector_instances")
    )
    ui_extensions = tuple(
        _ui_extension_from_mapping(item) for item in _mapping_items(payload, "ui_extensions")
    )
    migration_bundles = tuple(
        _migration_bundle_from_mapping(item)
        for item in _mapping_items(payload, "migration_bundles")
    )
    source_package = _source_package_from_mapping(
        _optional_mapping(payload.get("source_package")),
    )
    runtime_policies = _runtime_policies_from_mapping(
        _optional_mapping(payload.get("runtime_policies")),
    )

    profile = DeploymentProfile(
        schema_version=schema_version,
        profile_id=profile_id,
        display_name=display_name,
        installed_modules=installed_modules,
        enabled_capabilities=enabled_capabilities,
        connector_instances=connector_instances,
        ui_extensions=ui_extensions,
        migration_bundles=migration_bundles,
        source_package=source_package,
        runtime_policies=runtime_policies,
    )
    _validate_profile_references(profile)
    return profile


def generate_profile_manifest(
    profile: DeploymentProfile,
    *,
    module_loader: ConnectorModuleLoader | None = None,
    available_modules: Iterable[ConnectorModuleDescriptor] = (),
) -> ProfileManifest:
    """Generate a fail-closed runtime manifest from a deployment profile."""

    module_by_id = {module.module_id: module for module in available_modules}
    loader = module_loader or load_connector_module
    installed_modules: list[ConnectorModuleDescriptor] = []
    for module_entry in profile.installed_modules:
        module = module_by_id.get(module_entry.module_id)
        if module is None:
            module = loader(module_entry.import_path)
        _validate_installed_module(module_entry, module)
        installed_modules.append(module)

    installed_module_by_id: dict[str, ConnectorModuleDescriptor] = {
        module.module_id: module for module in installed_modules
    }
    profile_capabilities = _capabilities_with_builtin(profile)
    profile_instances = _instances_with_builtin(profile)

    _validate_profile_references(
        DeploymentProfile(
            schema_version=profile.schema_version,
            profile_id=profile.profile_id,
            display_name=profile.display_name,
            installed_modules=profile.installed_modules,
            enabled_capabilities=profile_capabilities,
            connector_instances=profile_instances,
            ui_extensions=profile.ui_extensions,
            migration_bundles=profile.migration_bundles,
            source_package=profile.source_package,
            runtime_policies=profile.runtime_policies,
        ),
    )
    _validate_module_descriptors(
        profile=profile,
        installed_modules=tuple(installed_modules),
        capabilities=profile_capabilities,
        instances=profile_instances,
    )

    api_routes: list[ConnectorApiRouteDescriptor] = []
    worker_hooks: list[ConnectorWorkerHookDescriptor] = []
    for module in installed_module_by_id.values():
        api_routes.extend(sorted(module.api_routes, key=lambda item: item.route_prefix))
        worker_hooks.extend(sorted(module.worker_hooks, key=lambda item: item.id))
    ui_extensions = tuple(
        sorted(
            (
                extension
                for module in installed_module_by_id.values()
                for extension in module.ui_extensions
            ),
            key=lambda item: item.id,
        ),
    )
    migration_bundles = tuple(
        sorted(
            (
                bundle
                for module in installed_module_by_id.values()
                for bundle in module.migration_bundles
            ),
            key=lambda item: item.id,
        ),
    )

    return ProfileManifest(
        schema_version=profile.schema_version,
        profile_id=profile.profile_id,
        installed_modules=tuple(installed_modules),
        capabilities=tuple(sorted(profile_capabilities, key=lambda item: item.id)),
        connector_instances=tuple(
            sorted(profile_instances, key=lambda item: item.connector_instance_id),
        ),
        api_routes=tuple(api_routes),
        worker_hooks=tuple(worker_hooks),
        ui_extensions=ui_extensions,
        migration_bundles=migration_bundles,
        source_package=profile.source_package,
        runtime_policies=profile.runtime_policies,
    )


def default_builtin_manifest(*, profile_id: str = "product") -> ProfileManifest:
    """Return a manifest with only built-in product capabilities."""

    profile = DeploymentProfile(
        schema_version=SUPPORTED_PROFILE_SCHEMA_VERSION,
        profile_id=profile_id,
        display_name=profile_id,
    )
    return generate_profile_manifest(profile)


def load_connector_module(import_path: str) -> ConnectorModuleDescriptor:
    """Load a connector module descriptor from `module:function` import path."""

    module_name, separator, function_name = import_path.partition(":")
    if not separator or not module_name or not function_name:
        raise ProfileValidationError(
            "Connector module import_path must use 'module:function' format.",
        )
    module = import_module(module_name)
    entrypoint = getattr(module, function_name, None)
    if not callable(entrypoint):
        raise ProfileValidationError(f"Connector module entry point not found: {import_path}.")
    descriptor = entrypoint()
    if not isinstance(descriptor, ConnectorModuleDescriptor):
        raise ProfileValidationError(
            f"Connector module entry point returned unsupported descriptor: {import_path}.",
        )
    return descriptor


def manifest_to_mapping(manifest: ProfileManifest) -> Mapping[str, object]:
    """Return a JSON/YAML-safe manifest mapping."""

    return {
        "schema_version": manifest.schema_version,
        "profile_id": manifest.profile_id,
        "installed_modules": [
            {
                "module_id": module.module_id,
                "connector_folder": module.connector_folder,
                "contract_version": module.contract_version,
                "api_router_entrypoint": module.api_router_entrypoint,
                "approved_document_handler_entrypoint": (
                    module.approved_document_handler_entrypoint
                ),
                "document_deletion_handler_entrypoint": (
                    module.document_deletion_handler_entrypoint
                ),
            }
            for module in manifest.installed_modules
        ],
        "capabilities": [
            _capability_to_mapping(capability) for capability in manifest.capabilities
        ],
        "connector_instances": [
            _instance_to_mapping(instance) for instance in manifest.connector_instances
        ],
        "api_routes": [
            {
                "module_id": route.module_id,
                "route_prefix": route.route_prefix,
                "capability_id": route.capability_id,
                "source": route.source,
                "connector": route.connector,
                "required_instance_id": route.required_instance_id,
            }
            for route in manifest.api_routes
        ],
        "worker_hooks": [
            {
                "module_id": hook.module_id,
                "id": hook.id,
                "capability_id": hook.capability_id,
                "required_instance_id": hook.required_instance_id,
            }
            for hook in manifest.worker_hooks
        ],
        "ui_extensions": [
            _ui_extension_to_mapping(ui_extension) for ui_extension in manifest.ui_extensions
        ],
        "migration_bundles": [
            {
                "id": bundle.id,
                "module_id": bundle.module_id,
                "path": bundle.path,
            }
            for bundle in manifest.migration_bundles
        ],
        "runtime_policies": _runtime_policies_to_mapping(manifest.runtime_policies),
    }


def _capabilities_with_builtin(
    profile: DeploymentProfile,
) -> tuple[ConnectorCapabilityDescriptor, ...]:
    capabilities = {capability.id: capability for capability in profile.enabled_capabilities}
    capabilities.setdefault(BUILTIN_MANUAL_UPLOAD_CAPABILITY_ID, manual_upload_capability())
    return tuple(capabilities.values())


def _instances_with_builtin(
    profile: DeploymentProfile,
) -> tuple[ConnectorInstanceDescriptor, ...]:
    instances = {
        instance.connector_instance_id: instance for instance in profile.connector_instances
    }
    builtin_instance = manual_upload_instance(profile_id=profile.profile_id)
    instances.setdefault(builtin_instance.connector_instance_id, builtin_instance)
    return tuple(instances.values())


def _validate_profile_references(profile: DeploymentProfile) -> None:
    source_package = profile.source_package
    if (
        source_package.allow_core_only_delivery or source_package.overlay_path is not None
    ) and source_package.delivery_target is not SourcePackageDeliveryTarget.CUSTOMER:
        raise ProfileValidationError(
            "Source-package core-only delivery and overlays require delivery_target: customer.",
        )
    if source_package.overlay_path is not None:
        expected_overlay_path = (
            Path("deployments") / profile.profile_id / "source-overlay"
        ).as_posix()
        if source_package.overlay_path != expected_overlay_path:
            raise ProfileValidationError(
                "source_package.overlay_path must equal "
                f"'{expected_overlay_path}' for profile '{profile.profile_id}'.",
            )

    module_ids = {module.module_id for module in profile.installed_modules}
    capability_ids = {capability.id for capability in profile.enabled_capabilities}
    instance_ids = {instance.connector_instance_id for instance in profile.connector_instances}
    capability_by_id = {capability.id: capability for capability in profile.enabled_capabilities}
    _reject_duplicate("installed module", module_ids, len(profile.installed_modules))
    _reject_duplicate("capability", capability_ids, len(profile.enabled_capabilities))
    _reject_duplicate("connector instance", instance_ids, len(profile.connector_instances))

    for capability in profile.enabled_capabilities:
        if capability.module_id is not None and capability.module_id not in module_ids:
            raise ProfileValidationError(
                f"Capability {capability.id} references uninstalled module {capability.module_id}.",
            )
    for instance in profile.connector_instances:
        if instance.capability_id not in capability_ids:
            raise ProfileValidationError(
                f"Instance {instance.connector_instance_id} references disabled capability "
                f"{instance.capability_id}.",
            )
        if instance.module_id is not None and instance.module_id not in module_ids:
            raise ProfileValidationError(
                f"Instance {instance.connector_instance_id} references uninstalled module "
                f"{instance.module_id}.",
            )
        capability = capability_by_id[instance.capability_id]
        if capability.module_id != instance.module_id:
            raise ProfileValidationError(
                f"Instance {instance.connector_instance_id} module_id must match capability "
                f"{instance.capability_id} module ownership.",
            )
    for ui_extension in profile.ui_extensions:
        if ui_extension.module_id not in module_ids:
            raise ProfileValidationError(
                f"UI extension {ui_extension.id} references uninstalled module "
                f"{ui_extension.module_id}.",
            )
        if ui_extension.capability_id not in capability_ids:
            raise ProfileValidationError(
                f"UI extension {ui_extension.id} references disabled capability "
                f"{ui_extension.capability_id}.",
            )
        if (
            ui_extension.required_instance_id is not None
            and ui_extension.required_instance_id not in instance_ids
        ):
            raise ProfileValidationError(
                f"UI extension {ui_extension.id} references unconfigured instance "
                f"{ui_extension.required_instance_id}.",
            )
    for migration_bundle in profile.migration_bundles:
        if migration_bundle.module_id not in module_ids:
            raise ProfileValidationError(
                f"Migration bundle {migration_bundle.id} references uninstalled module "
                f"{migration_bundle.module_id}.",
            )


def _validate_installed_module(
    entry: InstalledModuleProfileEntry,
    module: ConnectorModuleDescriptor,
) -> None:
    if module.module_id != entry.module_id:
        raise ProfileValidationError(
            f"Loaded connector module {module.module_id} does not match profile entry "
            f"{entry.module_id}.",
        )
    if module.connector_folder != entry.connector_folder:
        raise ProfileValidationError(
            f"Connector module {module.module_id} folder {module.connector_folder} does not "
            f"match profile entry {entry.connector_folder}.",
        )
    if module.api_router_entrypoint != entry.api_router_entrypoint:
        raise ProfileValidationError(
            f"Connector module {module.module_id} API router entrypoint does not match "
            "the profile manifest.",
        )
    if module.approved_document_handler_entrypoint != entry.approved_document_handler_entrypoint:
        raise ProfileValidationError(
            f"Connector module {module.module_id} approved document handler entrypoint "
            "does not match the profile manifest.",
        )
    if module.document_deletion_handler_entrypoint != entry.document_deletion_handler_entrypoint:
        raise ProfileValidationError(
            f"Connector module {module.module_id} document deletion handler entrypoint "
            "does not match the profile manifest.",
        )
    if module.api_routes and module.api_router_entrypoint is None:
        raise ProfileValidationError(
            f"Connector module {module.module_id} declares API routes without an API router "
            "entrypoint.",
        )
    if entry.api_route_prefixes and entry.api_router_entrypoint is None:
        raise ProfileValidationError(
            f"Profile entry {entry.module_id} allowlists API route prefixes without an API "
            "router entrypoint.",
        )


def _validate_module_descriptors(
    *,
    profile: DeploymentProfile,
    installed_modules: tuple[ConnectorModuleDescriptor, ...],
    capabilities: tuple[ConnectorCapabilityDescriptor, ...],
    instances: tuple[ConnectorInstanceDescriptor, ...],
) -> None:
    entry_by_module = {entry.module_id: entry for entry in profile.installed_modules}
    capability_ids = {capability.id for capability in capabilities}
    capability_by_id = {capability.id: capability for capability in capabilities}
    instance_ids = {instance.connector_instance_id for instance in instances}
    instance_by_id = {instance.connector_instance_id: instance for instance in instances}
    profile_ui_ids = {extension.id for extension in profile.ui_extensions}
    profile_ui_by_id = {extension.id: extension for extension in profile.ui_extensions}
    profile_migration_ids = {bundle.id for bundle in profile.migration_bundles}
    profile_migration_by_id = {bundle.id: bundle for bundle in profile.migration_bundles}
    module_ids = {module.module_id for module in installed_modules}
    module_capability_ids = {
        capability.id for module in installed_modules for capability in module.capabilities
    }
    module_ui_ids = {
        extension.id for module in installed_modules for extension in module.ui_extensions
    }
    module_migration_ids = {
        bundle.id for module in installed_modules for bundle in module.migration_bundles
    }

    for module in installed_modules:
        entry = entry_by_module[module.module_id]
        _ensure_declared(
            "route prefix",
            (route.route_prefix for route in module.api_routes),
            entry.api_route_prefixes,
            module.module_id,
        )
        _ensure_declared(
            "worker hook",
            (hook.id for hook in module.worker_hooks),
            entry.worker_hook_ids,
            module.module_id,
        )
        _ensure_declared(
            "migration bundle",
            (bundle.id for bundle in module.migration_bundles),
            entry.migration_bundle_ids,
            module.module_id,
        )
        _ensure_declared(
            "UI extension",
            (extension.id for extension in module.ui_extensions),
            entry.ui_extension_ids,
            module.module_id,
        )
        for capability in module.capabilities:
            if capability.id not in capability_ids:
                raise ProfileValidationError(
                    f"Module {module.module_id} capability {capability.id} is not enabled "
                    "by the profile manifest.",
                )
        for route in module.api_routes:
            if route.capability_id not in capability_ids:
                raise ProfileValidationError(
                    f"Route {route.route_prefix} references disabled capability "
                    f"{route.capability_id}.",
                )
            _ensure_capability_owned_by_module(
                capability_by_id[route.capability_id],
                module_id=module.module_id,
                owner_name=f"Route {route.route_prefix}",
            )
            if (
                route.required_instance_id is not None
                and route.required_instance_id not in instance_ids
            ):
                raise ProfileValidationError(
                    f"Route {route.route_prefix} references unconfigured instance "
                    f"{route.required_instance_id}.",
                )
            if route.required_instance_id is not None:
                _ensure_instance_owned_by_module(
                    instance_by_id[route.required_instance_id],
                    capability_id=route.capability_id,
                    module_id=module.module_id,
                    owner_name=f"Route {route.route_prefix}",
                )
        for hook in module.worker_hooks:
            if hook.capability_id not in capability_ids:
                raise ProfileValidationError(
                    f"Worker hook {hook.id} references disabled capability {hook.capability_id}.",
                )
            _ensure_capability_owned_by_module(
                capability_by_id[hook.capability_id],
                module_id=module.module_id,
                owner_name=f"Worker hook {hook.id}",
            )
            if (
                hook.required_instance_id is not None
                and hook.required_instance_id not in instance_ids
            ):
                raise ProfileValidationError(
                    f"Worker hook {hook.id} references unconfigured instance "
                    f"{hook.required_instance_id}.",
                )
            if hook.required_instance_id is not None:
                _ensure_instance_owned_by_module(
                    instance_by_id[hook.required_instance_id],
                    capability_id=hook.capability_id,
                    module_id=module.module_id,
                    owner_name=f"Worker hook {hook.id}",
                )
        for extension in module.ui_extensions:
            if extension.id not in profile_ui_ids:
                raise ProfileValidationError(
                    f"Module {module.module_id} UI extension {extension.id} is not in the "
                    "profile UI extension manifest.",
                )
            if extension != profile_ui_by_id[extension.id]:
                raise ProfileValidationError(
                    f"Module {module.module_id} UI extension {extension.id} does not match "
                    "the profile UI extension manifest.",
                )
        for bundle in module.migration_bundles:
            if bundle.id not in profile_migration_ids:
                raise ProfileValidationError(
                    f"Module {module.module_id} migration bundle {bundle.id} is not in the "
                    "profile migration plan.",
                )
            if bundle != profile_migration_by_id[bundle.id]:
                raise ProfileValidationError(
                    f"Module {module.module_id} migration bundle {bundle.id} does not match "
                    "the profile migration plan.",
                )
        for instance in instances:
            if instance.module_id == module.module_id:
                _validate_instance_config_schema(instance=instance, module=module)
    profile_only_module_capability_ids = {
        capability.id
        for capability in capabilities
        if capability.module_id in module_ids and capability.id not in module_capability_ids
    }
    if profile_only_module_capability_ids:
        extra = ", ".join(sorted(profile_only_module_capability_ids))
        raise ProfileValidationError(
            f"Profile capability manifest contains descriptors not declared by modules: {extra}.",
        )
    extra_profile_ui_ids = profile_ui_ids - module_ui_ids
    if extra_profile_ui_ids:
        extra = ", ".join(sorted(extra_profile_ui_ids))
        raise ProfileValidationError(
            f"Profile UI extension manifest contains descriptors not declared by modules: {extra}.",
        )
    extra_profile_migration_ids = profile_migration_ids - module_migration_ids
    if extra_profile_migration_ids:
        extra = ", ".join(sorted(extra_profile_migration_ids))
        raise ProfileValidationError(
            f"Profile migration plan contains bundles not declared by modules: {extra}.",
        )


def _ensure_declared(
    item_name: str,
    actual_values: Iterable[str],
    allowed_values: tuple[str, ...],
    module_id: str,
) -> None:
    allowed = set(allowed_values)
    actual_seen = set(actual_values)
    extra_allowed = allowed - actual_seen
    if extra_allowed:
        extra = ", ".join(sorted(extra_allowed))
        raise ProfileValidationError(
            f"Profile manifest allows {item_name} entries not declared by module {module_id}: "
            f"{extra}.",
        )
    for actual in actual_seen:
        if actual not in allowed:
            raise ProfileValidationError(
                f"Module {module_id} declared {item_name} {actual} outside the generated "
                "profile manifest.",
            )


def _ensure_capability_owned_by_module(
    capability: ConnectorCapabilityDescriptor,
    *,
    module_id: str,
    owner_name: str,
) -> None:
    if capability.module_id != module_id:
        raise ProfileValidationError(
            f"{owner_name} references capability {capability.id} outside module {module_id}.",
        )


def _ensure_instance_owned_by_module(
    instance: ConnectorInstanceDescriptor,
    *,
    capability_id: str,
    module_id: str,
    owner_name: str,
) -> None:
    if instance.capability_id != capability_id:
        raise ProfileValidationError(
            f"{owner_name} references instance {instance.connector_instance_id} bound to "
            f"capability {instance.capability_id}, not {capability_id}.",
        )
    if instance.module_id != module_id:
        raise ProfileValidationError(
            f"{owner_name} references instance {instance.connector_instance_id} outside "
            f"module {module_id}.",
        )


def _validate_instance_config_schema(
    *,
    instance: ConnectorInstanceDescriptor,
    module: ConnectorModuleDescriptor,
) -> None:
    missing_config = tuple(
        field_name
        for field_name in module.config_schema.non_secret_fields
        if field_name not in instance.config_references
    )
    missing_secrets = tuple(
        reference_name
        for reference_name in module.config_schema.secret_reference_names
        if reference_name not in instance.secret_references
    )
    if missing_config:
        missing = ", ".join(missing_config)
        raise ProfileValidationError(
            f"Instance {instance.connector_instance_id} is missing config references required "
            f"by module {module.module_id}: {missing}.",
        )
    if missing_secrets:
        missing = ", ".join(missing_secrets)
        raise ProfileValidationError(
            f"Instance {instance.connector_instance_id} is missing secret references required "
            f"by module {module.module_id}: {missing}.",
        )


def _reject_duplicate(item_name: str, unique_values: set[str], original_count: int) -> None:
    if len(unique_values) != original_count:
        raise ProfileValidationError(f"Duplicate {item_name} entries are not allowed.")


def _load_yaml_mapping(path: Path) -> Mapping[str, object]:
    if not path.exists():
        raise ProfileValidationError(f"Deployment profile does not exist: {path}.")
    safe_load = cast(YamlSafeLoad, import_module("yaml").safe_load)
    payload = safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProfileValidationError("Deployment profile must be a mapping.")
    return cast(Mapping[str, object], payload)


def _installed_module_from_mapping(
    payload: Mapping[str, object],
) -> InstalledModuleProfileEntry:
    return InstalledModuleProfileEntry(
        module_id=_required_str(payload, "module_id"),
        connector_folder=_required_str(payload, "connector_folder"),
        import_path=_required_str(payload, "import_path"),
        api_router_entrypoint=_optional_str(payload, "api_router_entrypoint"),
        approved_document_handler_entrypoint=_optional_str(
            payload,
            "approved_document_handler_entrypoint",
        ),
        document_deletion_handler_entrypoint=_optional_str(
            payload,
            "document_deletion_handler_entrypoint",
        ),
        api_route_prefixes=_str_tuple(payload, "api_route_prefixes"),
        worker_hook_ids=_str_tuple(payload, "worker_hook_ids"),
        migration_bundle_ids=_str_tuple(payload, "migration_bundle_ids"),
        ui_extension_ids=_str_tuple(payload, "ui_extension_ids"),
    )


def _capability_from_mapping(payload: Mapping[str, object]) -> ConnectorCapabilityDescriptor:
    return ConnectorCapabilityDescriptor(
        id=_required_str(payload, "id"),
        module_id=_optional_str(payload, "module_id"),
        kind=ConnectorCapabilityKind(_required_str(payload, "kind")),
        status=ConnectorStatus(_required_str(payload, "status")),
        visibility=ConnectorVisibility(_required_str(payload, "visibility")),
        safe_metadata=_safe_metadata_from_mapping(payload),
        ui_surfaces=_str_tuple(payload, "ui_surfaces"),
        required_permissions=_str_tuple(payload, "required_permissions"),
    )


def _instance_from_mapping(
    payload: Mapping[str, object],
    *,
    profile_id: str,
) -> ConnectorInstanceDescriptor:
    return ConnectorInstanceDescriptor(
        connector_instance_id=_required_str(payload, "connector_instance_id"),
        capability_id=_required_str(payload, "capability_id"),
        module_id=_optional_str(payload, "module_id"),
        profile_id=profile_id,
        status=ConnectorStatus(_required_str(payload, "status")),
        visibility=ConnectorVisibility(_required_str(payload, "visibility")),
        safe_metadata=_safe_metadata_from_mapping(payload),
        config_references=_str_mapping(payload, "config_references"),
        secret_references=_str_mapping(payload, "secret_references"),
        health=_str_mapping(payload, "health"),
    )


def _ui_extension_from_mapping(payload: Mapping[str, object]) -> ConnectorUiExtensionDescriptor:
    return ConnectorUiExtensionDescriptor(
        id=_required_str(payload, "id"),
        module_id=_required_str(payload, "module_id"),
        capability_id=_required_str(payload, "capability_id"),
        connector_folder=_required_str(payload, "connector_folder"),
        slot=_required_str(payload, "slot"),
        module_path=_required_str(payload, "module_path"),
        required_permissions=_str_tuple(payload, "required_permissions"),
        required_instance_id=_optional_str(payload, "required_instance_id"),
        safe_metadata=_safe_metadata_from_mapping(payload),
    )


def _migration_bundle_from_mapping(
    payload: Mapping[str, object],
) -> ConnectorMigrationBundleDescriptor:
    return ConnectorMigrationBundleDescriptor(
        id=_required_str(payload, "id"),
        module_id=_required_str(payload, "module_id"),
        path=_required_str(payload, "path"),
    )


def _source_package_from_mapping(payload: Mapping[str, object]) -> SourcePackageProfile:
    raw_delivery_target = _optional_str(payload, "delivery_target") or "internal"
    try:
        delivery_target = SourcePackageDeliveryTarget(raw_delivery_target)
    except ValueError as error:
        raise ProfileValidationError(
            "source_package.delivery_target must be 'internal' or 'customer'.",
        ) from error
    return SourcePackageProfile(
        delivery_target=delivery_target,
        include_paths=_str_tuple(payload, "include_paths"),
        forbidden_terms=_str_tuple(payload, "forbidden_terms"),
        allow_core_only_delivery=_optional_bool(
            payload,
            "allow_core_only_delivery",
            default=False,
        ),
        overlay_path=_optional_str(payload, "overlay_path"),
    )


def _runtime_policies_from_mapping(payload: Mapping[str, object]) -> RuntimePoliciesProfile:
    effective_requirements = _optional_mapping(payload.get("effective_attribute_requirements"))
    if not effective_requirements:
        return RuntimePoliciesProfile()
    if _required_str(effective_requirements, "kind") != _METADATA_BOOLEAN_MAKES_ALL_OPTIONAL:
        raise ProfileValidationError(
            f"effective_attribute_requirements.kind must be {_METADATA_BOOLEAN_MAKES_ALL_OPTIONAL}."
        )
    return RuntimePoliciesProfile(
        effective_attribute_requirements=EffectiveAttributeRequirementsPolicyProfile(
            trigger_metadata_key=_required_str(effective_requirements, "trigger_metadata_key"),
        ),
    )


def _safe_metadata_from_mapping(payload: Mapping[str, object]) -> SafeMetadata:
    metadata = _optional_mapping(payload.get("safe_metadata"))
    label = _optional_str(metadata, "label") or _required_str(payload, "display_name")
    return SafeMetadata(
        label=label,
        description=_optional_str(metadata, "description"),
        extra=_str_mapping(metadata, "extra"),
    )


def _capability_to_mapping(capability: ConnectorCapabilityDescriptor) -> Mapping[str, object]:
    return {
        "id": capability.id,
        "module_id": capability.module_id,
        "kind": capability.kind.value,
        "status": capability.status.value,
        "visibility": capability.visibility.value,
        "contract_version": capability.contract_version,
        "ui_surfaces": list(capability.ui_surfaces),
        "required_permissions": list(capability.required_permissions),
        "safe_metadata": _safe_metadata_to_mapping(capability.safe_metadata),
    }


def _instance_to_mapping(instance: ConnectorInstanceDescriptor) -> Mapping[str, object]:
    return {
        "connector_instance_id": instance.connector_instance_id,
        "capability_id": instance.capability_id,
        "module_id": instance.module_id,
        "profile_id": instance.profile_id,
        "status": instance.status.value,
        "visibility": instance.visibility.value,
        "config_references": dict(instance.config_references),
        "secret_references": dict(instance.secret_references),
        "health": dict(instance.health),
        "safe_metadata": _safe_metadata_to_mapping(instance.safe_metadata),
    }


def _ui_extension_to_mapping(
    ui_extension: ConnectorUiExtensionDescriptor,
) -> Mapping[str, object]:
    return {
        "id": ui_extension.id,
        "module_id": ui_extension.module_id,
        "capability_id": ui_extension.capability_id,
        "connector_folder": ui_extension.connector_folder,
        "slot": ui_extension.slot,
        "module_path": ui_extension.module_path,
        "required_permissions": list(ui_extension.required_permissions),
        "required_instance_id": ui_extension.required_instance_id,
        "safe_metadata": _safe_metadata_to_mapping(ui_extension.safe_metadata),
    }


def _safe_metadata_to_mapping(metadata: SafeMetadata) -> Mapping[str, object]:
    return {
        "label": metadata.label,
        "description": metadata.description,
        "extra": dict(metadata.extra),
    }


def _runtime_policies_to_mapping(policies: RuntimePoliciesProfile) -> Mapping[str, object]:
    policy = policies.effective_attribute_requirements
    if policy is None:
        return {}
    return {
        "effective_attribute_requirements": {
            "kind": _METADATA_BOOLEAN_MAKES_ALL_OPTIONAL,
            "trigger_metadata_key": policy.trigger_metadata_key,
        },
    }


def _mapping_items(payload: Mapping[str, object], key: str) -> tuple[Mapping[str, object], ...]:
    value = payload.get(key, [])
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ProfileValidationError(f"{key} must be a list.")
    items: list[Mapping[str, object]] = []
    for item in cast(list[object], value):
        if not isinstance(item, dict):
            raise ProfileValidationError(f"{key} entries must be mappings.")
        items.append(cast(Mapping[str, object], item))
    return tuple(items)


def _optional_mapping(value: object) -> Mapping[str, object]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, dict):
        raise ProfileValidationError("Expected a mapping value.")
    return cast(Mapping[str, object], value)


def _required_str(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProfileValidationError(f"{key} is required.")
    return value.strip()


def _optional_str(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProfileValidationError(f"{key} must be a string.")
    normalized = value.strip()
    return normalized or None


def _required_int(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ProfileValidationError(f"{key} must be an integer.")
    return value


def _optional_bool(payload: Mapping[str, object], key: str, *, default: bool) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ProfileValidationError(f"{key} must be a boolean.")
    return value


def _str_tuple(payload: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key, [])
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ProfileValidationError(f"{key} must be a list of strings.")
    result: list[str] = []
    for item in cast(list[object], value):
        if not isinstance(item, str) or not item.strip():
            raise ProfileValidationError(f"{key} must contain only non-empty strings.")
        result.append(item.strip())
    return tuple(result)


def _str_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, str]:
    value = payload.get(key, {})
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, dict):
        raise ProfileValidationError(f"{key} must be a mapping.")
    result: dict[str, str] = {}
    for raw_key, raw_value in cast(dict[object, object], value).items():
        if not isinstance(raw_key, str) or not isinstance(raw_value, str):
            raise ProfileValidationError(f"{key} must contain only string keys and values.")
        result[raw_key] = raw_value
    return MappingProxyType(result)
