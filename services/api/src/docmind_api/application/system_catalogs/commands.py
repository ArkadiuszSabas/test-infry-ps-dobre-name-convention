"""System catalog command and error types."""

from dataclasses import dataclass
from uuid import UUID

from docmind_api.domain.system_catalogs.models import (
    SystemCatalogDisplayMode,
    SystemCatalogDisplayPartSourceType,
    SystemCatalogExtensionField,
    SystemCatalogExtensionValueType,
)
from docmind_backend_runtime.errors import NotFoundError, ValidationApplicationError


@dataclass(frozen=True, slots=True)
class SaveSystemCatalogExtensionFieldCommand:
    """Input for one system catalog extension field."""

    code: str
    label: str
    value_type: SystemCatalogExtensionValueType
    dictionary_id: UUID | str | None
    mapped_attribute_definition_id: UUID | str | None
    is_required: bool
    show_in_overview: bool
    field_order: int
    is_active: bool = True
    id: UUID | str | None = None


@dataclass(frozen=True, slots=True)
class SaveSystemCatalogDisplayModePartCommand:
    """Input for one display mode part."""

    part_order: int
    source_type: SystemCatalogDisplayPartSourceType
    extension_field_id: UUID | str | None = None
    extension_field_code: str | None = None
    separator_before: str | None = None
    id: UUID | str | None = None


@dataclass(frozen=True, slots=True)
class SaveSystemCatalogDisplayModeCommand:
    """Input for one display mode."""

    name: str
    is_default: bool
    is_active: bool
    parts: tuple[SaveSystemCatalogDisplayModePartCommand, ...]
    id: UUID | str | None = None


@dataclass(frozen=True, slots=True)
class SaveSystemCatalogDefinitionCommand:
    """Input for replacing the definition of one system catalog."""

    system_catalog_key: str
    fields: tuple[SaveSystemCatalogExtensionFieldCommand, ...]
    display_modes: tuple[SaveSystemCatalogDisplayModeCommand, ...]


@dataclass(frozen=True, slots=True)
class SystemCatalogDefinition:
    """Read model for one system catalog definition."""

    system_catalog_key: str
    fields: tuple[SystemCatalogExtensionField, ...]
    display_modes: tuple[SystemCatalogDisplayMode, ...]


class SystemCatalogNotFoundError(NotFoundError):
    """Raised when a system catalog key is not supported."""

    def __init__(self, *, system_catalog_key: object) -> None:
        key = str(system_catalog_key)
        super().__init__(
            code="SYSTEM_CATALOG_NOT_FOUND",
            message="System catalog not found.",
            details={"system_catalog_key": key},
        )


class SystemCatalogValidationError(ValidationApplicationError):
    """Raised when system catalog configuration is invalid."""

    def __init__(self, *, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(
            code="SYSTEM_CATALOG_VALIDATION_ERROR",
            message=message,
            details=details,
        )
