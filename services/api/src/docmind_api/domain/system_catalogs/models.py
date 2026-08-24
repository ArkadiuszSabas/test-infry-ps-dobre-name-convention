"""System catalog extension models and invariants."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

DOCUMENT_TYPE_SYSTEM_CATALOG_KEY = "document_type"
SYSTEM_CATALOG_CODE_MAX_LENGTH = 80
SYSTEM_CATALOG_KEY_MAX_LENGTH = 80
SYSTEM_CATALOG_LABEL_MAX_LENGTH = 200
SYSTEM_CATALOG_SEPARATOR_MAX_LENGTH = 32
SYSTEM_CATALOG_TEXT_VALUE_MAX_LENGTH = 2000


class SystemCatalogExtensionValueType(StrEnum):
    """Supported extension field value types."""

    DICTIONARY = "dictionary"
    TEXT = "text"


class SystemCatalogDisplayPartSourceType(StrEnum):
    """Supported display mode part sources."""

    BASE_NAME = "base_name"
    EXTENSION_FIELD = "extension_field"


@dataclass(frozen=True, slots=True)
class SystemCatalogExtensionField:
    """Configurable field attached to a system catalog entry."""

    id: UUID | str
    system_catalog_key: str
    code: str
    label: str
    value_type: SystemCatalogExtensionValueType
    dictionary_id: UUID | str | None
    mapped_attribute_definition_id: UUID | str | None
    is_required: bool
    show_in_overview: bool
    field_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", UUID(str(self.id)))
        object.__setattr__(
            self,
            "system_catalog_key",
            normalize_system_catalog_key(self.system_catalog_key),
        )
        object.__setattr__(self, "code", normalize_system_catalog_code(self.code))
        object.__setattr__(self, "label", normalize_system_catalog_label(self.label))
        value_type = SystemCatalogExtensionValueType(self.value_type)
        object.__setattr__(self, "value_type", value_type)
        object.__setattr__(self, "dictionary_id", _normalize_optional_uuid(self.dictionary_id))
        object.__setattr__(
            self,
            "mapped_attribute_definition_id",
            _normalize_optional_uuid(self.mapped_attribute_definition_id),
        )
        object.__setattr__(self, "field_order", normalize_non_negative_int(self.field_order))
        if value_type == SystemCatalogExtensionValueType.DICTIONARY:
            if self.dictionary_id is None:
                raise ValueError("Dictionary extension fields require dictionary_id.")
        elif self.dictionary_id is not None:
            raise ValueError("Text extension fields cannot reference dictionary_id.")
        if self.created_at > self.updated_at:
            raise ValueError(
                "System catalog extension field updated_at cannot be before created_at."
            )


@dataclass(frozen=True, slots=True)
class SystemCatalogDisplayModePart:
    """One ordered component of a system catalog display label."""

    id: UUID | str
    display_mode_id: UUID | str
    part_order: int
    source_type: SystemCatalogDisplayPartSourceType
    extension_field_id: UUID | str | None
    separator_before: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", UUID(str(self.id)))
        object.__setattr__(self, "display_mode_id", UUID(str(self.display_mode_id)))
        object.__setattr__(self, "part_order", normalize_non_negative_int(self.part_order))
        source_type = SystemCatalogDisplayPartSourceType(self.source_type)
        object.__setattr__(self, "source_type", source_type)
        object.__setattr__(
            self,
            "extension_field_id",
            _normalize_optional_uuid(self.extension_field_id),
        )
        object.__setattr__(
            self,
            "separator_before",
            normalize_separator(self.separator_before),
        )
        if source_type == SystemCatalogDisplayPartSourceType.BASE_NAME:
            if self.extension_field_id is not None:
                raise ValueError("Base-name display parts cannot reference extension_field_id.")
        elif self.extension_field_id is None:
            raise ValueError("Extension-field display parts require extension_field_id.")


@dataclass(frozen=True, slots=True)
class SystemCatalogDisplayMode:
    """A configured label composition for one system catalog."""

    id: UUID | str
    system_catalog_key: str
    name: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    parts: tuple[SystemCatalogDisplayModePart, ...]

    def __post_init__(self) -> None:
        normalized_id = UUID(str(self.id))
        object.__setattr__(self, "id", normalized_id)
        object.__setattr__(
            self,
            "system_catalog_key",
            normalize_system_catalog_key(self.system_catalog_key),
        )
        object.__setattr__(self, "name", normalize_system_catalog_label(self.name))
        if self.created_at > self.updated_at:
            raise ValueError("System catalog display mode updated_at cannot be before created_at.")
        for part in self.parts:
            if UUID(str(part.display_mode_id)) != normalized_id:
                raise ValueError("Display mode parts must reference their display mode.")


@dataclass(frozen=True, slots=True)
class DocumentTypeExtensionValue:
    """Stored extension value for one document type and extension field."""

    id: UUID | str
    document_type_id: UUID | str
    extension_field_id: UUID | str
    dictionary_entry_id: UUID | str | None
    text_value: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", UUID(str(self.id)))
        object.__setattr__(self, "document_type_id", UUID(str(self.document_type_id)))
        object.__setattr__(self, "extension_field_id", UUID(str(self.extension_field_id)))
        object.__setattr__(
            self,
            "dictionary_entry_id",
            _normalize_optional_uuid(self.dictionary_entry_id),
        )
        object.__setattr__(self, "text_value", normalize_extension_text_value(self.text_value))
        if self.created_at > self.updated_at:
            raise ValueError(
                "Document type extension value updated_at cannot be before created_at."
            )


def normalize_system_catalog_key(value: str) -> str:
    """Validate and return a system catalog key."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("System catalog key is required.")
    if len(normalized) > SYSTEM_CATALOG_KEY_MAX_LENGTH:
        raise ValueError(
            f"System catalog key cannot exceed {SYSTEM_CATALOG_KEY_MAX_LENGTH} characters.",
        )
    return normalized


def normalize_system_catalog_code(value: str) -> str:
    """Validate and return an extension field code."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("System catalog field code is required.")
    if len(normalized) > SYSTEM_CATALOG_CODE_MAX_LENGTH:
        raise ValueError(
            f"System catalog field code cannot exceed {SYSTEM_CATALOG_CODE_MAX_LENGTH} characters.",
        )
    return normalized


def normalize_system_catalog_label(value: str) -> str:
    """Validate and return a display label."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("System catalog label is required.")
    if len(normalized) > SYSTEM_CATALOG_LABEL_MAX_LENGTH:
        raise ValueError(
            f"System catalog label cannot exceed {SYSTEM_CATALOG_LABEL_MAX_LENGTH} characters.",
        )
    return normalized


def normalize_extension_text_value(value: str | None) -> str | None:
    """Normalize a text extension value."""

    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > SYSTEM_CATALOG_TEXT_VALUE_MAX_LENGTH:
        raise ValueError(
            "System catalog text value cannot exceed "
            f"{SYSTEM_CATALOG_TEXT_VALUE_MAX_LENGTH} characters.",
        )
    return normalized


def normalize_separator(value: str | None) -> str | None:
    """Normalize an optional display label separator."""

    if value is None:
        return None
    if not value:
        return None
    if len(value) > SYSTEM_CATALOG_SEPARATOR_MAX_LENGTH:
        raise ValueError(
            "System catalog display separator cannot exceed "
            f"{SYSTEM_CATALOG_SEPARATOR_MAX_LENGTH} characters.",
        )
    return value


def normalize_non_negative_int(value: int) -> int:
    """Validate and return a non-negative integer."""

    if isinstance(value, bool):
        raise ValueError("System catalog order values must be integers.")
    if value < 0:
        raise ValueError("System catalog order values cannot be negative.")
    return value


def _normalize_optional_uuid(value: UUID | str | None) -> UUID | None:
    if value is None:
        return None
    return UUID(str(value))
