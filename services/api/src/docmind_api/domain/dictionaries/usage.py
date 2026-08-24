"""Custom dictionary usage counters."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DictionaryUsage:
    """Dependency counts that can block dictionary deletion or deactivation."""

    attribute_bindings: int = 0
    active_attribute_bindings: int = 0
    system_catalog_fields: int = 0
    active_system_catalog_fields: int = 0
    entries: int = 0

    def __post_init__(self) -> None:
        for field_name, value in self.as_details().items():
            if type(value) is not int or value < 0:
                raise ValueError(f"Dictionary usage count cannot be negative: {field_name}.")

    @property
    def has_blocking_dependencies(self) -> bool:
        """Return whether any dependency blocks permanent deletion."""

        return self.attribute_bindings > 0 or self.system_catalog_fields > 0 or self.entries > 0

    @property
    def blocking_dependencies(self) -> tuple[str, ...]:
        """Return dependency names that currently block deletion."""

        dependencies: list[str] = []
        if self.attribute_bindings:
            dependencies.append("attribute_bindings")
        if self.system_catalog_fields:
            dependencies.append("system_catalog_fields")
        if self.entries:
            dependencies.append("entries")
        return tuple(dependencies)

    def as_details(self) -> dict[str, int]:
        """Return API-safe usage details."""

        return {
            "attribute_bindings": self.attribute_bindings,
            "active_attribute_bindings": self.active_attribute_bindings,
            "system_catalog_fields": self.system_catalog_fields,
            "active_system_catalog_fields": self.active_system_catalog_fields,
            "entries": self.entries,
        }


@dataclass(frozen=True, slots=True)
class DictionaryEntryUsage:
    """Dependency counts that can block permanent entry deletion."""

    document_metadata_values: int = 0
    document_type_extension_values: int = 0

    def __post_init__(self) -> None:
        for field_name, value in self.as_details().items():
            if type(value) is not int or value < 0:
                raise ValueError(f"Dictionary entry usage count cannot be negative: {field_name}.")

    @property
    def has_blocking_dependencies(self) -> bool:
        """Return whether any dependency blocks permanent deletion."""

        return self.document_metadata_values > 0 or self.document_type_extension_values > 0

    @property
    def blocking_dependencies(self) -> tuple[str, ...]:
        """Return dependency names that currently block deletion."""

        dependencies: list[str] = []
        if self.document_metadata_values:
            dependencies.append("document_metadata_values")
        if self.document_type_extension_values:
            dependencies.append("document_type_extension_values")
        return tuple(dependencies)

    def as_details(self) -> dict[str, int]:
        """Return API-safe usage details."""

        return {
            "document_metadata_values": self.document_metadata_values,
            "document_type_extension_values": self.document_type_extension_values,
        }
