"""Attribute definition usage models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AttributeDefinitionUsage:
    """Blocking dependency counts for an attribute definition."""

    document_type_mappings: int = 0
    active_document_type_mappings: int = 0
    system_catalog_fields: int = 0
    active_configurations: int = 0
    historical_values: int = 0

    def __post_init__(self) -> None:
        for field_name, value in self.as_details().items():
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative.")

    @property
    def has_blocking_dependencies(self) -> bool:
        """Return whether this usage prevents permanent deletion."""

        return bool(self.blocking_dependencies)

    @property
    def blocking_dependencies(self) -> tuple[str, ...]:
        """Return dependency categories with at least one use."""

        return tuple(name for name, value in self.as_details().items() if value > 0)

    def as_details(self) -> dict[str, int]:
        """Return API-safe dependency counts."""

        return {
            "document_type_mappings": self.document_type_mappings,
            "active_document_type_mappings": self.active_document_type_mappings,
            "system_catalog_fields": self.system_catalog_fields,
            "active_configurations": self.active_configurations,
            "historical_values": self.historical_values,
        }
