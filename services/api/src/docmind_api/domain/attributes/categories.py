"""System attribute category models and policy flags."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

from docmind_api.domain.attributes.constants import (
    ATTRIBUTE_CATEGORY_MAX_LENGTH,
    ATTRIBUTE_ID_MAX_LENGTH,
)
from docmind_api.domain.attributes.enums import AttributeStatus
from docmind_api.domain.attributes.identifiers import normalize_attribute_external_id

ATTRIBUTE_CATEGORY_IS_METADATA_FLAG = "isMetadata"
ATTRIBUTE_CATEGORY_DEFAULT_EXTERNAL_ID = "bez_kategorii"
ATTRIBUTE_CATEGORY_METADATA_EXTERNAL_ID = "metadata"

type AttributeCategoryFlags = Mapping[str, bool]


@dataclass(frozen=True, slots=True)
class AttributeCategory:
    """A system-owned category that can classify attribute definitions."""

    id: UUID | str
    external_id: str
    label: str
    flags: AttributeCategoryFlags
    status: AttributeStatus
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", UUID(str(self.id)))
        object.__setattr__(
            self,
            "external_id",
            normalize_attribute_external_id(self.external_id),
        )
        object.__setattr__(self, "label", normalize_attribute_category_label(self.label))
        object.__setattr__(self, "flags", MappingProxyType(dict(self.flags)))
        object.__setattr__(self, "status", AttributeStatus(self.status))
        if self.created_at > self.updated_at:
            raise ValueError("Attribute category updated_at cannot be before created_at.")
        for flag_name, flag_value in self.flags.items():
            if not flag_name.strip():
                raise ValueError("Attribute category flag names cannot be empty.")
            if len(flag_name) > ATTRIBUTE_ID_MAX_LENGTH:
                raise ValueError(
                    "Attribute category flag names cannot exceed "
                    f"{ATTRIBUTE_ID_MAX_LENGTH} characters.",
                )
            if type(flag_value) is not bool:
                raise ValueError("Attribute category flags must be booleans.")

    @property
    def is_active(self) -> bool:
        """Return whether this category can be selected for new attributes."""

        return self.status == AttributeStatus.ACTIVE

    def update_business_fields(
        self,
        *,
        label: str,
        flags: AttributeCategoryFlags,
        updated_at: datetime,
    ) -> AttributeCategory:
        """Return an updated category without changing stable identity fields."""

        return AttributeCategory(
            id=self.id,
            external_id=self.external_id,
            label=label,
            flags=flags,
            status=self.status,
            created_at=self.created_at,
            updated_at=updated_at,
        )

    def deactivate(self, *, updated_at: datetime) -> AttributeCategory:
        """Return this category marked inactive."""

        return AttributeCategory(
            id=self.id,
            external_id=self.external_id,
            label=self.label,
            flags=self.flags,
            status=AttributeStatus.INACTIVE,
            created_at=self.created_at,
            updated_at=updated_at,
        )


@dataclass(frozen=True, slots=True)
class AttributeCategoryUsage:
    """Counts of dependencies that can block category lifecycle actions."""

    attribute_definitions: int = 0
    active_attribute_definitions: int = 0

    @property
    def has_blocking_dependencies(self) -> bool:
        """Return whether the category cannot be permanently deleted."""

        return self.attribute_definitions > 0

    @property
    def has_active_dependencies(self) -> bool:
        """Return whether the category cannot be deactivated."""

        return self.active_attribute_definitions > 0

    @property
    def blocking_dependencies(self) -> tuple[str, ...]:
        """Return non-zero dependency kinds for error details."""

        dependencies: list[str] = []
        if self.attribute_definitions > 0:
            dependencies.append("attribute_definitions")
        return tuple(dependencies)

    def as_details(self) -> dict[str, int]:
        """Return serializable dependency counts."""

        return {
            "attribute_definitions": self.attribute_definitions,
            "active_attribute_definitions": self.active_attribute_definitions,
        }


def normalize_attribute_category_label(value: str) -> str:
    """Validate and return the category display label."""

    normalized = value.strip()
    if not normalized:
        raise ValueError("Attribute category label is required.")
    if len(normalized) > ATTRIBUTE_CATEGORY_MAX_LENGTH:
        raise ValueError(
            f"Attribute category label cannot exceed {ATTRIBUTE_CATEGORY_MAX_LENGTH} characters.",
        )

    return normalized


def attribute_category_is_metadata(category: AttributeCategory) -> bool:
    """Return whether a category contains document metadata attributes."""

    return category.flags.get(ATTRIBUTE_CATEGORY_IS_METADATA_FLAG) is True
