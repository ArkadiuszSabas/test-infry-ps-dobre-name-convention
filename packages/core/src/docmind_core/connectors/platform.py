"""Framework-free connector platform context and ports."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from docmind_core.connectors.profiles import ProfileManifest


class ConnectorPlatformError(ValueError):
    """Raised when a connector requests platform access outside its manifest."""


@dataclass(frozen=True, slots=True)
class ConnectorDocumentTypeSelector:
    """Exact catalog lookup with a configured fallback document type."""

    name: str
    parameters: Mapping[str, str]
    fallback_document_type_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "document type name"))
        object.__setattr__(
            self,
            "parameters",
            _document_type_selector_parameters(self.parameters),
        )
        object.__setattr__(
            self,
            "fallback_document_type_id",
            _required_text(self.fallback_document_type_id, "fallback document type id"),
        )


@dataclass(frozen=True, slots=True)
class ConnectorDocumentTypeExternalIdSelector:
    """Exact external-id catalog lookup with a configured fallback document type."""

    external_id: str
    parameters: Mapping[str, str]
    fallback_document_type_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "external_id",
            _required_text(self.external_id, "document type external id"),
        )
        object.__setattr__(
            self,
            "parameters",
            _document_type_selector_parameters(self.parameters),
        )
        object.__setattr__(
            self,
            "fallback_document_type_id",
            _required_text(self.fallback_document_type_id, "fallback document type id"),
        )


@dataclass(frozen=True, slots=True)
class ConnectorDocumentIntakeRequest:
    """Generic in-process document intake request produced by a connector route."""

    original_filename: str
    content: bytes
    document_type_id: str | None = None
    document_type_selector: (
        ConnectorDocumentTypeSelector | ConnectorDocumentTypeExternalIdSelector | None
    ) = None
    metadata_values: Mapping[str, object] = field(
        default_factory=lambda: MappingProxyType({}),
    )
    name: str | None = None
    external_id: str | None = None
    connector_correlation_id: str | None = None
    content_type: str | None = None
    start_ocr_pipeline: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "original_filename",
            _required_text(self.original_filename, "original filename"),
        )
        if (self.document_type_id is None) == (self.document_type_selector is None):
            raise ValueError("Exactly one document type id or document type selector is required.")
        object.__setattr__(self, "document_type_id", _optional_text(self.document_type_id))
        if not self.content:
            raise ValueError("content is required.")
        object.__setattr__(self, "metadata_values", MappingProxyType(dict(self.metadata_values)))
        object.__setattr__(self, "name", _optional_text(self.name))
        object.__setattr__(self, "external_id", _optional_text(self.external_id))
        object.__setattr__(
            self,
            "connector_correlation_id",
            _optional_text(self.connector_correlation_id),
        )
        object.__setattr__(self, "content_type", _optional_text(self.content_type))


@dataclass(frozen=True, slots=True)
class ConnectorDocumentIntakeResult:
    """Minimal result returned by the generic document intake platform port."""

    document_id: str
    connector_instance_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "document_id", _required_text(self.document_id, "document id"))
        object.__setattr__(
            self,
            "connector_instance_id",
            _runtime_id(self.connector_instance_id, "connector instance id"),
        )


class ConnectorDocumentIntakePort(Protocol):
    """Port exposed to connector routes for generic DocMind document intake."""

    async def ingest_document(
        self,
        route_context: ConnectorRouteContext,
        request: ConnectorDocumentIntakeRequest,
    ) -> ConnectorDocumentIntakeResult:
        """Store and register a connector-normalized document in-process."""
        ...


class ConnectorConfigurationPort(Protocol):
    """Read manifest-bound non-secret connector values for one request."""

    async def get_values(self, route_context: ConnectorRouteContext) -> Mapping[str, str] | None:
        """Return durable values, or ``None`` when no admin configuration exists yet."""
        ...


class ConnectorDocumentArchiveStatus(StrEnum):
    """Durable status of one connector-owned approved-document archive operation."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConnectorDocumentArchiveFailureStage(StrEnum):
    """Stage at which one connector archive attempt failed."""

    PREFLIGHT = "preflight"
    IO = "io"


@dataclass(frozen=True, slots=True)
class ConnectorApprovedDocument:
    """Approved document content and source metadata exposed to its owning connector."""

    document_id: UUID
    connector_instance_id: str
    content: bytes
    metadata_values: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "connector_instance_id",
            _runtime_id(self.connector_instance_id, "connector instance id"),
        )
        if not self.content:
            raise ValueError("approved document content is required.")
        object.__setattr__(self, "metadata_values", MappingProxyType(dict(self.metadata_values)))


@dataclass(frozen=True, slots=True)
class ConnectorApprovedDocumentCommand:
    """Committed approval that may trigger one manifest-selected connector handler."""

    document_id: UUID
    connector_instance_id: str
    review_version: int
    approved_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "connector_instance_id",
            _runtime_id(self.connector_instance_id, "connector instance id"),
        )
        if self.review_version < 1:
            raise ValueError("review_version must be positive.")
        if self.approved_at.tzinfo is None:
            raise ValueError("approved_at must be timezone-aware.")


@dataclass(frozen=True, slots=True)
class ConnectorDocumentArchivePlan:
    """Deterministic target reserved before connector archive IO starts."""

    document_id: UUID
    connector_instance_id: str
    handler_id: str
    review_version: int
    approved_at: datetime
    folder_path: str
    file_name: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "connector_instance_id",
            _runtime_id(self.connector_instance_id, "connector instance id"),
        )
        object.__setattr__(self, "handler_id", _runtime_id(self.handler_id, "handler id"))
        if self.review_version < 1:
            raise ValueError("review_version must be positive.")
        if self.approved_at.tzinfo is None:
            raise ValueError("approved_at must be timezone-aware.")
        object.__setattr__(self, "folder_path", _required_text(self.folder_path, "folder path"))
        object.__setattr__(self, "file_name", _required_text(self.file_name, "file name"))


@dataclass(frozen=True, slots=True)
class ConnectorDocumentArchive:
    """Durable connector archive state returned through the neutral platform context."""

    plan: ConnectorDocumentArchivePlan
    status: ConnectorDocumentArchiveStatus
    drive_item_id: str | None
    web_url: str | None
    error_code: str | None
    failure_stage: ConnectorDocumentArchiveFailureStage | None
    created_at: datetime
    updated_at: datetime


class ConnectorDocumentApprovalContext(Protocol):
    """Narrow product surfaces available to an approved-document connector handler."""

    async def load_document(self, document_id: UUID) -> ConnectorApprovedDocument: ...

    async def resolve_document_attribute(
        self,
        document: ConnectorApprovedDocument,
        *,
        review_version: int,
        attribute_definition_id: UUID,
    ) -> object | None: ...

    async def get_configuration(self, connector_instance_id: str) -> Mapping[str, str] | None: ...

    def get_secret(self, connector_instance_id: str, reference_name: str) -> str | None: ...

    async def reserve_archive(
        self,
        plan: ConnectorDocumentArchivePlan,
    ) -> ConnectorDocumentArchive: ...

    async def archive_succeeded(
        self,
        plan: ConnectorDocumentArchivePlan,
        *,
        drive_item_id: str,
        web_url: str,
    ) -> ConnectorDocumentArchive: ...

    async def archive_failed(
        self,
        plan: ConnectorDocumentArchivePlan,
        *,
        error_code: str,
        failure_stage: ConnectorDocumentArchiveFailureStage,
    ) -> ConnectorDocumentArchive: ...


ConnectorApprovedDocumentHandler = Callable[
    [ConnectorApprovedDocumentCommand, ConnectorDocumentApprovalContext],
    Awaitable[None],
]


class ConnectorDocumentDeletionPhase(StrEnum):
    """Side-effect boundary for one connector-owned deletion decision."""

    PLAN = "plan"
    PREPARE = "prepare"


class ConnectorDocumentDeletionPolicy(StrEnum):
    """Connector policy for external artifacts related to a DocMind document."""

    NOT_APPLICABLE = "not_applicable"
    PRESERVE = "preserve"
    DELETE = "delete"
    BLOCK = "block"


class ConnectorDocumentDeletionPreparationStatus(StrEnum):
    """Safe connector preparation result consumed by the product deletion flow."""

    READY = "ready"
    RETRYABLE_FAILURE = "retryable_failure"
    BLOCKED = "blocked"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class ConnectorDocumentDeletionCommand:
    """Minimal document provenance exposed to the manifest-selected deletion handler."""

    document_id: UUID
    connector_instance_id: str
    phase: ConnectorDocumentDeletionPhase
    archived: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "connector_instance_id",
            _runtime_id(self.connector_instance_id, "connector instance id"),
        )


@dataclass(frozen=True, slots=True)
class ConnectorDocumentDeletionResult:
    """Display-safe impact and preparation state returned by a connector."""

    policy: ConnectorDocumentDeletionPolicy
    status: ConnectorDocumentDeletionPreparationStatus
    warning_code: str | None = None
    error_code: str | None = None
    preserved_artifact_labels: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warning_code", _optional_text(self.warning_code))
        object.__setattr__(self, "error_code", _optional_text(self.error_code))
        object.__setattr__(
            self,
            "preserved_artifact_labels",
            tuple(
                _required_text(label, "preserved artifact label")
                for label in self.preserved_artifact_labels
            ),
        )
        if self.status is ConnectorDocumentDeletionPreparationStatus.READY:
            if self.error_code is not None:
                raise ValueError("Ready document deletion result cannot include an error code.")
        elif self.error_code is None:
            raise ValueError("Non-ready document deletion result requires an error code.")
        if self.policy is ConnectorDocumentDeletionPolicy.BLOCK:
            if self.status is ConnectorDocumentDeletionPreparationStatus.READY:
                raise ValueError("Blocked deletion policy cannot be ready.")


class ConnectorDocumentDeletionContext(Protocol):
    """Narrow neutral state surface available to connector deletion handlers."""

    async def get_archive(self, document_id: UUID) -> ConnectorDocumentArchive | None: ...

    async def is_archive_active(self, document_id: UUID) -> bool: ...

    async def cancel_archive(
        self,
        document_id: UUID,
        *,
        error_code: str,
    ) -> ConnectorDocumentArchive | None: ...


ConnectorDocumentDeletionHandler = Callable[
    [ConnectorDocumentDeletionCommand, ConnectorDocumentDeletionContext],
    Awaitable[ConnectorDocumentDeletionResult],
]


class _UnconfiguredConnectorConfigurationPort:
    """Preserve connector test fixtures that do not expose configuration storage."""

    async def get_values(self, route_context: ConnectorRouteContext) -> Mapping[str, str] | None:
        return None


@dataclass(frozen=True, slots=True)
class ConnectorRouteContext:
    """Manifest-verified route context safe to pass to connector route code."""

    profile_id: str
    module_id: str
    route_prefix: str
    capability_id: str
    source: str
    connector: str
    connector_instance_id: str | None = None

    @property
    def audit_actor(self) -> str:
        """Return the synthetic connector actor for audit records."""

        if self.connector_instance_id is not None:
            return f"connector:{self.connector_instance_id}"
        return f"connector:{self.capability_id}"


ConnectorApiKeyDependency = Callable[..., str | Awaitable[str]]
ConnectorApiKeyDependencyFactory = Callable[[ConnectorRouteContext], ConnectorApiKeyDependency]


@dataclass(frozen=True, slots=True)
class ConnectorApiRegistrationContext:
    """Manifest-only API context exposed during connector route registration."""

    manifest: ProfileManifest

    def require_route(
        self,
        *,
        module_id: str,
        route_prefix: str,
        capability_id: str,
        connector_instance_id: str | None = None,
    ) -> ConnectorRouteContext:
        """Return a route context only when the route is allowlisted by the manifest."""

        normalized_module_id = _runtime_id(module_id, "module id")
        normalized_route_prefix = _route_prefix(route_prefix)
        normalized_capability_id = _runtime_id(capability_id, "capability id")
        normalized_instance_id = (
            _runtime_id(connector_instance_id, "connector instance id")
            if connector_instance_id is not None
            else None
        )

        module_ids = {module.module_id for module in self.manifest.installed_modules}
        if normalized_module_id not in module_ids:
            raise ConnectorPlatformError(
                f"Connector module is not installed by this profile: {normalized_module_id}.",
            )

        route = next(
            (
                item
                for item in self.manifest.api_routes
                if item.route_prefix == normalized_route_prefix
                and item.module_id == normalized_module_id
            ),
            None,
        )
        if route is None:
            raise ConnectorPlatformError(
                f"Connector route is not allowlisted by this profile: {normalized_route_prefix}.",
            )
        if route.capability_id != normalized_capability_id:
            raise ConnectorPlatformError(
                f"Connector route {normalized_route_prefix} is bound to capability "
                f"{route.capability_id}, not {normalized_capability_id}.",
            )

        capability = next(
            (item for item in self.manifest.capabilities if item.id == normalized_capability_id),
            None,
        )
        if capability is None or capability.module_id != normalized_module_id:
            raise ConnectorPlatformError(
                f"Capability {normalized_capability_id} is not owned by module "
                f"{normalized_module_id}.",
            )

        effective_instance_id = normalized_instance_id or route.required_instance_id
        if route.required_instance_id is not None and (
            effective_instance_id != route.required_instance_id
        ):
            raise ConnectorPlatformError(
                f"Connector route {normalized_route_prefix} requires instance "
                f"{route.required_instance_id}.",
            )
        if effective_instance_id is not None:
            self._require_instance(
                connector_instance_id=effective_instance_id,
                capability_id=normalized_capability_id,
                module_id=normalized_module_id,
            )

        return ConnectorRouteContext(
            profile_id=self.manifest.profile_id,
            module_id=normalized_module_id,
            route_prefix=normalized_route_prefix,
            capability_id=normalized_capability_id,
            source=route.source or normalized_capability_id,
            connector=route.connector or normalized_capability_id,
            connector_instance_id=effective_instance_id,
        )

    def _require_instance(
        self,
        *,
        connector_instance_id: str,
        capability_id: str,
        module_id: str,
    ) -> None:
        instance = next(
            (
                item
                for item in self.manifest.connector_instances
                if item.connector_instance_id == connector_instance_id
            ),
            None,
        )
        if instance is None:
            raise ConnectorPlatformError(
                f"Connector instance is not configured by this profile: {connector_instance_id}.",
            )
        if instance.capability_id != capability_id:
            raise ConnectorPlatformError(
                f"Connector instance {connector_instance_id} is bound to capability "
                f"{instance.capability_id}, not {capability_id}.",
            )
        if instance.module_id != module_id:
            raise ConnectorPlatformError(
                f"Connector instance {connector_instance_id} is not owned by module {module_id}.",
            )


@dataclass(frozen=True, slots=True)
class ConnectorApiPlatformContext:
    """Narrow API platform context exposed to connector request handlers."""

    manifest: ProfileManifest
    document_intake: ConnectorDocumentIntakePort
    configuration: ConnectorConfigurationPort = field(
        default_factory=_UnconfiguredConnectorConfigurationPort,
    )
    max_content_bytes: int = 25 * 1024 * 1024

    def __post_init__(self) -> None:
        if self.max_content_bytes < 1:
            raise ValueError("connector content limit must be positive.")

    def require_route(
        self,
        *,
        module_id: str,
        route_prefix: str,
        capability_id: str,
        connector_instance_id: str | None = None,
    ) -> ConnectorRouteContext:
        """Return a route context only when the route is allowlisted by the manifest."""

        return ConnectorApiRegistrationContext(manifest=self.manifest).require_route(
            module_id=module_id,
            route_prefix=route_prefix,
            capability_id=capability_id,
            connector_instance_id=connector_instance_id,
        )


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


def _document_type_selector_parameters(
    parameters: Mapping[str, str],
) -> Mapping[str, str]:
    normalized = MappingProxyType(
        {
            _required_text(key, "document type parameter name"): _required_text(
                value,
                "document type parameter value",
            )
            for key, value in parameters.items()
        }
    )
    if not normalized:
        raise ValueError("document type selector parameters are required.")
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


def _route_prefix(value: str) -> str:
    normalized = _required_text(value, "route prefix").rstrip("/")
    if not normalized.startswith("/"):
        raise ValueError("route prefix must start with '/'.")
    if "//" in normalized:
        raise ValueError("route prefix must not contain empty path segments.")
    return normalized
