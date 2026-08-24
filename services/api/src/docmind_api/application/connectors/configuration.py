"""Application service for manifest-bound connector configuration."""

from __future__ import annotations

import hmac
import json
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from docmind_api.domain.attributes.models import AttributeDefinition, AttributeStatus
from docmind_api.domain.connectors.configuration import ConnectorInstanceConfiguration
from docmind_backend_runtime.errors import ConflictError, ValidationApplicationError
from docmind_core.connectors import (
    ConnectorConfigurationTestResult,
    ConnectorModuleDescriptor,
    ConnectorRouteContext,
    ConnectorStatus,
    ProfileManifest,
)


class ConnectorConfigurationError(ValidationApplicationError):
    """Raised for configuration requests outside the active profile."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="CONNECTOR_CONFIGURATION_VALIDATION_ERROR",
            message=message,
            details={},
        )


class ConnectorConfigurationConflictError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            code="CONNECTOR_CONFIGURATION_VERSION_CONFLICT",
            message="Connector configuration changed. Reload it before saving.",
            details={},
        )


class ConnectorConfigurationRepository(Protocol):
    async def get(
        self,
        connector_instance_id: str,
    ) -> ConnectorInstanceConfiguration | None: ...

    async def save(
        self,
        value: ConnectorInstanceConfiguration,
        *,
        expected_updated_at: datetime | None,
        expected_api_key_hash: str | None,
    ) -> ConnectorInstanceConfiguration | None: ...


class ConnectorAttributeDefinitionReferenceCatalog(Protocol):
    async def get_by_id(self, attribute_id: UUID) -> AttributeDefinition | None: ...


@dataclass(frozen=True, slots=True)
class SaveConnectorConfigurationCommand:
    values: Mapping[str, str]
    expected_updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RotateConnectorApiKeyCommand:
    expected_updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class TestConnectorConfigurationCommand:
    """Request an external connection test without saving the supplied values."""

    values: Mapping[str, str]
    test_id: str | None = None


@dataclass(frozen=True, slots=True)
class SavedConnectorConfiguration:
    configuration: ConnectorInstanceConfiguration
    generated_api_key: str | None


class ConnectorConfigurationService:
    """Own profile validation, safe reads and API-key hash verification."""

    def __init__(
        self,
        *,
        manifest: ProfileManifest,
        repository: ConnectorConfigurationRepository,
        attribute_repository: ConnectorAttributeDefinitionReferenceCatalog | None = None,
    ) -> None:
        self._manifest = manifest
        self._repository = repository
        self._attribute_repository = attribute_repository

    async def get(self, connector_instance_id: str) -> ConnectorInstanceConfiguration | None:
        self._require_instance(connector_instance_id)
        return await self._repository.get(connector_instance_id)

    def field_names(self, connector_instance_id: str) -> tuple[str, ...]:
        """Return only safe, connector-declared non-secret field names."""

        return self._require_instance(connector_instance_id).config_schema.non_secret_fields

    async def save(
        self,
        connector_instance_id: str,
        command: SaveConnectorConfigurationCommand,
    ) -> SavedConnectorConfiguration:
        module = self._require_instance(connector_instance_id)
        allowed = set(module.config_schema.non_secret_fields)
        values = {key.strip(): value.strip() for key, value in command.values.items()}
        if set(values) != allowed or any(not value for value in values.values()):
            raise ConnectorConfigurationError(
                "Connector configuration fields do not match its schema."
            )
        if module.configuration_validator is not None:
            try:
                module.configuration_validator(values)
            except ValueError as error:
                raise ConnectorConfigurationError(str(error)) from error
        await self._validate_attribute_definition_references(module, values)
        await self._validate_attribute_definition_mappings(module, values)
        existing = await self._repository.get(connector_instance_id)
        if existing is not None and command.expected_updated_at != existing.updated_at:
            raise ConnectorConfigurationConflictError()
        if existing is None and command.expected_updated_at is not None:
            raise ConnectorConfigurationConflictError()
        salt = existing.api_key_salt if existing is not None else None
        digest = existing.api_key_hash if existing is not None else None
        now = datetime.now(UTC)
        configuration = await self._repository.save(
            ConnectorInstanceConfiguration(
                connector_instance_id=connector_instance_id,
                values=values,
                api_key_salt=salt,
                api_key_hash=digest,
                created_at=existing.created_at if existing is not None else now,
                updated_at=now,
            ),
            expected_updated_at=command.expected_updated_at,
            expected_api_key_hash=existing.api_key_hash if existing is not None else None,
        )
        if configuration is None:
            raise ConnectorConfigurationConflictError()
        return SavedConnectorConfiguration(
            configuration=configuration,
            generated_api_key=None,
        )

    async def rotate_api_key(
        self,
        connector_instance_id: str,
        command: RotateConnectorApiKeyCommand,
    ) -> SavedConnectorConfiguration:
        """Generate one new inbound key without changing non-secret configuration."""

        self._require_instance(connector_instance_id)
        existing = await self._repository.get(connector_instance_id)
        if existing is not None and command.expected_updated_at != existing.updated_at:
            raise ConnectorConfigurationConflictError()
        if existing is None and command.expected_updated_at is not None:
            raise ConnectorConfigurationConflictError()

        generated_api_key = secrets.token_urlsafe(32)
        salt = secrets.token_hex(16)
        now = datetime.now(UTC)
        configuration = await self._repository.save(
            ConnectorInstanceConfiguration(
                connector_instance_id=connector_instance_id,
                values=existing.values if existing is not None else {},
                api_key_salt=salt,
                api_key_hash=_api_key_digest(generated_api_key, salt),
                created_at=existing.created_at if existing is not None else now,
                updated_at=now,
            ),
            expected_updated_at=command.expected_updated_at,
            expected_api_key_hash=existing.api_key_hash if existing is not None else None,
        )
        if configuration is None:
            raise ConnectorConfigurationConflictError()
        return SavedConnectorConfiguration(
            configuration=configuration,
            generated_api_key=generated_api_key,
        )

    async def test(
        self,
        connector_instance_id: str,
        command: TestConnectorConfigurationCommand,
    ) -> ConnectorConfigurationTestResult:
        """Validate and test current browser values without persisting them."""

        module = self._require_instance(connector_instance_id)
        values = {key.strip(): value.strip() for key, value in command.values.items()}
        allowed = set(module.config_schema.non_secret_fields)
        if set(values) != allowed or any(not value for value in values.values()):
            raise ConnectorConfigurationError(
                "Connector configuration fields do not match its schema."
            )
        if module.configuration_validator is not None:
            try:
                module.configuration_validator(values)
            except ValueError as error:
                raise ConnectorConfigurationError(str(error)) from error
        await self._validate_attribute_definition_references(module, values)
        await self._validate_attribute_definition_mappings(module, values)
        if module.configuration_tester is None:
            raise ConnectorConfigurationError(
                "Connector configuration does not support a connection test."
            )
        test_id = command.test_id.strip() if command.test_id is not None else None
        if command.test_id is not None and not test_id:
            raise ConnectorConfigurationError("Connector configuration test id is required.")
        return await module.configuration_tester.test(values, test_id=test_id)

    async def validate_api_key(
        self,
        route_context: ConnectorRouteContext,
        provided_key: str | None,
    ) -> bool:
        if route_context.connector_instance_id is None:
            return False
        if not self._is_route_enabled(route_context):
            return False
        record = await self.get(route_context.connector_instance_id)
        if record is None or not record.api_key_configured or provided_key is None:
            return False
        assert record.api_key_salt is not None and record.api_key_hash is not None
        return hmac.compare_digest(
            _api_key_digest(provided_key, record.api_key_salt),
            record.api_key_hash,
        )

    async def values_for_route(
        self,
        route_context: ConnectorRouteContext,
    ) -> Mapping[str, str] | None:
        if route_context.connector_instance_id is None:
            return None
        record = await self.get(route_context.connector_instance_id)
        return record.values if record is not None else None

    def _require_instance(self, connector_instance_id: str):
        instance = next(
            (
                item
                for item in self._manifest.connector_instances
                if item.connector_instance_id == connector_instance_id
            ),
            None,
        )
        if instance is None or instance.module_id is None:
            raise ConnectorConfigurationError(
                "Connector instance is not configurable in this profile."
            )
        module = next(
            (
                item
                for item in self._manifest.installed_modules
                if item.module_id == instance.module_id
            ),
            None,
        )
        if module is None:
            raise ConnectorConfigurationError("Connector module is not installed by this profile.")
        return module

    def _is_route_enabled(self, route_context: ConnectorRouteContext) -> bool:
        connector_instance_id = route_context.connector_instance_id
        if connector_instance_id is None:
            return False
        instance = next(
            (
                item
                for item in self._manifest.connector_instances
                if item.connector_instance_id == connector_instance_id
            ),
            None,
        )
        capability = next(
            (
                item
                for item in self._manifest.capabilities
                if item.id == route_context.capability_id
            ),
            None,
        )
        return (
            instance is not None
            and capability is not None
            and instance.status is ConnectorStatus.ENABLED
            and capability.status is ConnectorStatus.ENABLED
        )

    async def _validate_attribute_definition_references(
        self,
        module: ConnectorModuleDescriptor,
        values: Mapping[str, str],
    ) -> None:
        fields = module.config_schema.attribute_definition_reference_fields
        if not fields:
            return
        if self._attribute_repository is None:
            raise ConnectorConfigurationError(
                "Attribute definition catalog is unavailable for connector configuration.",
            )
        for field_name in fields:
            try:
                attribute_id = UUID(values[field_name])
            except ValueError as error:
                raise ConnectorConfigurationError(
                    f"Connector configuration field {field_name} must reference "
                    "an attribute definition UUID.",
                ) from error
            attribute = await self._attribute_repository.get_by_id(attribute_id)
            if attribute is None or attribute.status is not AttributeStatus.ACTIVE:
                raise ConnectorConfigurationError(
                    f"Connector configuration field {field_name} must reference "
                    "an active attribute definition.",
                )

    async def _validate_attribute_definition_mappings(
        self,
        module: ConnectorModuleDescriptor,
        values: Mapping[str, str],
    ) -> None:
        fields = module.config_schema.attribute_definition_mapping_fields
        if not fields:
            return
        if self._attribute_repository is None:
            raise ConnectorConfigurationError(
                "Attribute definition catalog is unavailable for connector configuration.",
            )
        for field_name in fields:
            attribute_ids = _attribute_definition_ids_from_mapping(
                field_name,
                values[field_name],
            )
            for attribute_id in attribute_ids:
                attribute = await self._attribute_repository.get_by_id(attribute_id)
                if attribute is None or attribute.status is not AttributeStatus.ACTIVE:
                    raise ConnectorConfigurationError(
                        f"Connector configuration field {field_name} must reference "
                        "only active attribute definitions.",
                    )


def _attribute_definition_ids_from_mapping(
    field_name: str,
    value: str,
) -> tuple[UUID, ...]:
    try:
        payload: object = json.loads(value)
    except json.JSONDecodeError as error:
        raise ConnectorConfigurationError(
            f"Connector configuration field {field_name} must contain valid JSON.",
        ) from error
    if not isinstance(payload, list):
        raise ConnectorConfigurationError(
            f"Connector configuration field {field_name} must contain a JSON list.",
        )
    attribute_ids: list[UUID] = []
    for item in cast(list[object], payload):
        if not isinstance(item, dict):
            raise ConnectorConfigurationError(
                f"Connector configuration field {field_name} contains an invalid mapping.",
            )
        raw_attribute_id = cast(dict[object, object], item).get("attribute_definition_id")
        if not isinstance(raw_attribute_id, str):
            raise ConnectorConfigurationError(
                f"Connector configuration field {field_name} contains an invalid "
                "attribute definition UUID.",
            )
        try:
            attribute_ids.append(UUID(raw_attribute_id))
        except ValueError as error:
            raise ConnectorConfigurationError(
                f"Connector configuration field {field_name} contains an invalid "
                "attribute definition UUID.",
            ) from error
    return tuple(attribute_ids)


def _api_key_digest(value: str, salt: str) -> str:
    return hmac.new(bytes.fromhex(salt), value.encode(), "sha256").hexdigest()
