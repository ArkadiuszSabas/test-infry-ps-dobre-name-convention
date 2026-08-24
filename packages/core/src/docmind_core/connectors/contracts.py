"""Framework-free connector foundation contracts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

BUILTIN_MANUAL_UPLOAD_CAPABILITY_ID = "manual_upload"
BUILTIN_MANUAL_UPLOAD_INSTANCE_ID = "core.manual_upload.primary"
BUILTIN_MANUAL_UPLOAD_SOURCE = "manual_upload"
BUILTIN_MANUAL_UPLOAD_CONNECTOR = "manual_upload"
SUPPORTED_CONNECTOR_CONTRACT_VERSION = 1


class ConnectorCapabilityKind(StrEnum):
    """Runtime-safe connector capability categories."""

    INPUT = "input"
    WORKFLOW = "workflow"
    TECHNICAL_ADAPTER = "technical_adapter"
    EXPORT = "export"


class ConnectorStatus(StrEnum):
    """Safe runtime status values exposed by capability manifests."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    UNCONFIGURED = "unconfigured"
    DEGRADED = "degraded"


class ConnectorConfigurationTestStatus(StrEnum):
    """Safe outcome categories returned by connector configuration tests."""

    SUCCESS = "success"
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SECRET_UNAVAILABLE = "secret_unavailable"
    SITE_NOT_FOUND = "site_not_found"
    LIBRARY_NOT_FOUND = "library_not_found"
    FOLDER_NOT_FOUND = "folder_not_found"
    COLUMN_NOT_FOUND = "column_not_found"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"


class ConnectorConfigurationTestDiagnosticStatus(StrEnum):
    """Display-safe state of one configuration-test diagnostic step."""

    INFO = "info"
    SUCCESS = "success"
    ERROR = "error"


class ConnectorVisibility(StrEnum):
    """Capability or instance visibility for API/UI clients."""

    PUBLIC = "public"
    ADMIN = "admin"
    INTERNAL = "internal"
    HIDDEN = "hidden"


@dataclass(frozen=True, slots=True)
class SafeMetadata:
    """Display-safe metadata that must not carry secrets or raw payloads."""

    label: str
    description: str | None = None
    extra: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "label", _required_text(self.label, "label"))
        object.__setattr__(self, "description", _optional_text(self.description))
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


@dataclass(frozen=True, slots=True)
class ConnectorCapabilityDescriptor:
    """Safe capability metadata exposed by API and profile manifests."""

    id: str
    kind: ConnectorCapabilityKind
    status: ConnectorStatus
    visibility: ConnectorVisibility
    safe_metadata: SafeMetadata
    module_id: str | None = None
    contract_version: int = SUPPORTED_CONNECTOR_CONTRACT_VERSION
    ui_surfaces: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _runtime_id(self.id, "capability id"))
        object.__setattr__(self, "module_id", _optional_runtime_id(self.module_id, "module id"))
        _validate_contract_version(self.contract_version)
        object.__setattr__(self, "ui_surfaces", _text_tuple(self.ui_surfaces, "ui surface"))
        object.__setattr__(
            self,
            "required_permissions",
            _text_tuple(self.required_permissions, "required permission"),
        )


@dataclass(frozen=True, slots=True)
class ConnectorInstanceDescriptor:
    """Configured connector instance safe to expose at runtime."""

    connector_instance_id: str
    capability_id: str
    status: ConnectorStatus
    visibility: ConnectorVisibility
    safe_metadata: SafeMetadata
    module_id: str | None = None
    profile_id: str | None = None
    config_references: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({}),
    )
    secret_references: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({}),
    )
    health: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "connector_instance_id",
            _runtime_id(self.connector_instance_id, "connector instance id"),
        )
        object.__setattr__(
            self,
            "capability_id",
            _runtime_id(self.capability_id, "capability id"),
        )
        object.__setattr__(self, "module_id", _optional_runtime_id(self.module_id, "module id"))
        object.__setattr__(self, "profile_id", _optional_runtime_id(self.profile_id, "profile id"))
        object.__setattr__(
            self, "config_references", MappingProxyType(dict(self.config_references))
        )
        object.__setattr__(
            self, "secret_references", MappingProxyType(dict(self.secret_references))
        )
        object.__setattr__(self, "health", MappingProxyType(dict(self.health)))


@dataclass(frozen=True, slots=True)
class ConnectorApiRouteDescriptor:
    """Connector-owned API route prefix declared by a module."""

    module_id: str
    route_prefix: str
    capability_id: str
    source: str | None = None
    connector: str | None = None
    required_instance_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "module_id", _runtime_id(self.module_id, "module id"))
        object.__setattr__(self, "route_prefix", _route_prefix(self.route_prefix))
        object.__setattr__(self, "capability_id", _runtime_id(self.capability_id, "capability id"))
        object.__setattr__(
            self,
            "source",
            _optional_runtime_id(self.source, "source") or self.capability_id,
        )
        object.__setattr__(
            self,
            "connector",
            _optional_runtime_id(self.connector, "connector") or self.capability_id,
        )
        object.__setattr__(
            self,
            "required_instance_id",
            _optional_runtime_id(self.required_instance_id, "connector instance id"),
        )


@dataclass(frozen=True, slots=True)
class ConnectorWorkerHookDescriptor:
    """Worker hook metadata declared by a connector module."""

    module_id: str
    id: str
    capability_id: str
    required_instance_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "module_id", _runtime_id(self.module_id, "module id"))
        object.__setattr__(self, "id", _runtime_id(self.id, "worker hook id"))
        object.__setattr__(self, "capability_id", _runtime_id(self.capability_id, "capability id"))
        object.__setattr__(
            self,
            "required_instance_id",
            _optional_runtime_id(self.required_instance_id, "connector instance id"),
        )


@dataclass(frozen=True, slots=True)
class ConnectorMigrationBundleDescriptor:
    """Connector-owned migration bundle metadata for profile plans."""

    id: str
    module_id: str
    path: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _runtime_id(self.id, "migration bundle id"))
        object.__setattr__(self, "module_id", _runtime_id(self.module_id, "module id"))
        object.__setattr__(self, "path", _relative_path(self.path, "migration bundle path"))


@dataclass(frozen=True, slots=True)
class ConnectorUiExtensionDescriptor:
    """Connector-owned UI extension descriptor selected by profile manifests."""

    id: str
    module_id: str
    capability_id: str
    connector_folder: str
    slot: str
    module_path: str
    required_permissions: tuple[str, ...] = ()
    required_instance_id: str | None = None
    safe_metadata: SafeMetadata = field(
        default_factory=lambda: SafeMetadata(label="Connector extension"),
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _runtime_id(self.id, "ui extension id"))
        object.__setattr__(self, "module_id", _runtime_id(self.module_id, "module id"))
        object.__setattr__(self, "capability_id", _runtime_id(self.capability_id, "capability id"))
        object.__setattr__(
            self,
            "connector_folder",
            _connector_folder(self.connector_folder),
        )
        object.__setattr__(self, "slot", _required_text(self.slot, "ui slot"))
        object.__setattr__(self, "module_path", _relative_path(self.module_path, "module path"))
        object.__setattr__(
            self,
            "required_permissions",
            _text_tuple(self.required_permissions, "required permission"),
        )
        object.__setattr__(
            self,
            "required_instance_id",
            _optional_runtime_id(self.required_instance_id, "connector instance id"),
        )
        expected_prefix = f"packages/connectors/{self.connector_folder}/web/"
        if not self.module_path.startswith(expected_prefix):
            raise ValueError(
                f"UI extension module_path must stay under {expected_prefix}.",
            )


@dataclass(frozen=True, slots=True)
class ConnectorConfigSchemaDescriptor:
    """Connector config schema metadata without secret values."""

    non_secret_fields: tuple[str, ...] = ()
    attribute_definition_reference_fields: tuple[str, ...] = ()
    attribute_definition_mapping_fields: tuple[str, ...] = ()
    secret_reference_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        non_secret_fields = _text_tuple(self.non_secret_fields, "config field")
        object.__setattr__(
            self,
            "non_secret_fields",
            non_secret_fields,
        )
        attribute_reference_fields = _text_tuple(
            self.attribute_definition_reference_fields,
            "attribute definition reference field",
        )
        if not set(attribute_reference_fields).issubset(non_secret_fields):
            raise ValueError(
                "Attribute definition reference fields must be declared non-secret fields.",
            )
        object.__setattr__(
            self,
            "attribute_definition_reference_fields",
            attribute_reference_fields,
        )
        attribute_mapping_fields = _text_tuple(
            self.attribute_definition_mapping_fields,
            "attribute definition mapping field",
        )
        if not set(attribute_mapping_fields).issubset(non_secret_fields):
            raise ValueError(
                "Attribute definition mapping fields must be declared non-secret fields.",
            )
        overlapping_attribute_fields = set(attribute_reference_fields) & set(
            attribute_mapping_fields
        )
        if overlapping_attribute_fields:
            raise ValueError(
                "Connector configuration fields cannot be both attribute definition "
                "references and attribute definition mappings.",
            )
        object.__setattr__(
            self,
            "attribute_definition_mapping_fields",
            attribute_mapping_fields,
        )
        object.__setattr__(
            self,
            "secret_reference_names",
            _text_tuple(self.secret_reference_names, "secret reference name"),
        )


@dataclass(frozen=True, slots=True)
class ConnectorConfigurationTestDiagnostic:
    """One ordered, display-safe diagnostic step from a connector test."""

    code: str
    status: ConnectorConfigurationTestDiagnosticStatus
    details: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _required_text(self.code, "diagnostic code"))
        object.__setattr__(
            self,
            "details",
            MappingProxyType(
                {
                    _required_text(key, "diagnostic detail key"): _required_text(
                        value,
                        "diagnostic detail value",
                    )
                    for key, value in self.details.items()
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class ConnectorConfigurationTestResult:
    """A display-safe result from one connector-owned configuration test."""

    status: ConnectorConfigurationTestStatus
    operation: str | None = None
    failure_code: str | None = None
    http_status_code: int | None = None
    diagnostics: tuple[ConnectorConfigurationTestDiagnostic, ...] = ()


class ConnectorConfigurationTester(Protocol):
    """Test unsaved non-secret connector configuration without persistence."""

    def test(
        self,
        values: Mapping[str, str],
        *,
        test_id: str | None = None,
    ) -> Awaitable[ConnectorConfigurationTestResult]: ...


@dataclass(frozen=True, slots=True)
class ConnectorModuleDescriptor:
    """Top-level connector module descriptor returned by a module entry point."""

    module_id: str
    connector_folder: str
    contract_version: int = SUPPORTED_CONNECTOR_CONTRACT_VERSION
    api_router_entrypoint: str | None = None
    approved_document_handler_entrypoint: str | None = None
    document_deletion_handler_entrypoint: str | None = None
    capabilities: tuple[ConnectorCapabilityDescriptor, ...] = ()
    api_routes: tuple[ConnectorApiRouteDescriptor, ...] = ()
    worker_hooks: tuple[ConnectorWorkerHookDescriptor, ...] = ()
    migration_bundles: tuple[ConnectorMigrationBundleDescriptor, ...] = ()
    ui_extensions: tuple[ConnectorUiExtensionDescriptor, ...] = ()
    config_schema: ConnectorConfigSchemaDescriptor = field(
        default_factory=ConnectorConfigSchemaDescriptor,
    )
    configuration_validator: Callable[[Mapping[str, str]], None] | None = None
    configuration_tester: ConnectorConfigurationTester | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "module_id", _runtime_id(self.module_id, "module id"))
        object.__setattr__(self, "connector_folder", _connector_folder(self.connector_folder))
        _validate_contract_version(self.contract_version)
        object.__setattr__(
            self,
            "api_router_entrypoint",
            _optional_entrypoint_path(self.api_router_entrypoint, "api router entrypoint"),
        )
        object.__setattr__(
            self,
            "approved_document_handler_entrypoint",
            _optional_entrypoint_path(
                self.approved_document_handler_entrypoint,
                "approved document handler entrypoint",
            ),
        )
        object.__setattr__(
            self,
            "document_deletion_handler_entrypoint",
            _optional_entrypoint_path(
                self.document_deletion_handler_entrypoint,
                "document deletion handler entrypoint",
            ),
        )
        for capability in self.capabilities:
            if capability.module_id != self.module_id:
                raise ValueError("Connector capability module_id must match descriptor module_id.")
        for route in self.api_routes:
            if route.module_id != self.module_id:
                raise ValueError("API route module_id must match descriptor module_id.")
        for worker_hook in self.worker_hooks:
            if worker_hook.module_id != self.module_id:
                raise ValueError("Worker hook module_id must match descriptor module_id.")
        for migration_bundle in self.migration_bundles:
            if migration_bundle.module_id != self.module_id:
                raise ValueError("Migration bundle module_id must match descriptor module_id.")
        for ui_extension in self.ui_extensions:
            if ui_extension.module_id != self.module_id:
                raise ValueError("UI extension module_id must match descriptor module_id.")
            if ui_extension.connector_folder != self.connector_folder:
                raise ValueError("UI extension connector_folder must match descriptor folder.")


def manual_upload_capability() -> ConnectorCapabilityDescriptor:
    """Return the built-in manual upload capability descriptor."""

    return ConnectorCapabilityDescriptor(
        id=BUILTIN_MANUAL_UPLOAD_CAPABILITY_ID,
        kind=ConnectorCapabilityKind.INPUT,
        status=ConnectorStatus.ENABLED,
        visibility=ConnectorVisibility.PUBLIC,
        safe_metadata=SafeMetadata(label="Manual upload"),
        ui_surfaces=("inbox.upload",),
        required_permissions=("documents.create",),
    )


def manual_upload_instance(*, profile_id: str) -> ConnectorInstanceDescriptor:
    """Return the built-in manual upload instance descriptor for a profile."""

    return ConnectorInstanceDescriptor(
        connector_instance_id=BUILTIN_MANUAL_UPLOAD_INSTANCE_ID,
        capability_id=BUILTIN_MANUAL_UPLOAD_CAPABILITY_ID,
        profile_id=profile_id,
        status=ConnectorStatus.ENABLED,
        visibility=ConnectorVisibility.PUBLIC,
        safe_metadata=SafeMetadata(label="Manual upload"),
    )


def _validate_contract_version(value: int) -> None:
    if value != SUPPORTED_CONNECTOR_CONTRACT_VERSION:
        raise ValueError(f"Unsupported connector contract version: {value}.")


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _runtime_id(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name)
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    if normalized.lower() != normalized or any(
        character not in allowed for character in normalized
    ):
        raise ValueError(f"{field_name} must use lowercase letters, digits, '.', '_' or '-'.")
    if normalized[0] in "._-" or normalized[-1] in "._-":
        raise ValueError(f"{field_name} must not start or end with a separator.")
    if ".." in normalized or "__" in normalized or "--" in normalized:
        raise ValueError(f"{field_name} must not contain repeated separators.")
    return normalized


def _optional_runtime_id(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _runtime_id(value, field_name)


def _connector_folder(value: str) -> str:
    normalized = _runtime_id(value, "connector folder")
    if "/" in normalized or "\\" in normalized:
        raise ValueError("connector folder must be a single path segment.")
    return normalized


def _route_prefix(value: str) -> str:
    normalized = _required_text(value, "route prefix").rstrip("/")
    if not normalized.startswith("/"):
        raise ValueError("route prefix must start with '/'.")
    if "//" in normalized:
        raise ValueError("route prefix must not contain empty path segments.")
    return normalized


def _relative_path(value: str, field_name: str) -> str:
    raw = _required_text(value.replace("\\", "/"), field_name)
    path = raw.strip("/")
    if raw.startswith("/") or ":" in raw or path.startswith("../") or "/../" in path:
        raise ValueError(f"{field_name} must not escape its package root.")
    return path


def _optional_entrypoint_path(value: str | None, field_name: str) -> str | None:
    normalized = _optional_text(value)
    if normalized is None:
        return None
    module_name, separator, function_name = normalized.partition(":")
    if not separator or not module_name.strip() or not function_name.strip():
        raise ValueError(f"{field_name} must use 'module:function' format.")
    return normalized


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    return tuple(_required_text(value, field_name) for value in values)
