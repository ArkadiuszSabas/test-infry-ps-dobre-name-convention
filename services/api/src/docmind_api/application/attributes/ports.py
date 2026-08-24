"""Application ports for the attribute definition catalog."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from docmind_api.domain.attributes.models import (
    AttributeCategory,
    AttributeCategoryUsage,
    AttributeDefinition,
    AttributeDefinitionUsage,
)
from docmind_api.domain.dictionaries.models import Dictionary


@dataclass(frozen=True, slots=True)
class AttributeCategoryCount:
    """Attribute count for one display category."""

    category: str
    count: int


class Clock(Protocol):
    """Port for obtaining audit timestamps."""

    def now(self) -> datetime: ...


class AttributeDefinitionIdFactory(Protocol):
    """Port for creating attribute definition identifiers."""

    def new_id(self) -> UUID: ...


class AttributeDefinitionRepository(Protocol):
    """Port implemented by attribute definition persistence adapters."""

    async def add(self, attribute: AttributeDefinition) -> bool: ...

    async def get_by_id(self, attribute_id: UUID | str) -> AttributeDefinition | None: ...

    async def get_by_external_id(self, external_id: str) -> AttributeDefinition | None: ...

    async def list(self, *, category: str | None = None) -> tuple[AttributeDefinition, ...]: ...

    async def count_by_category(self) -> tuple[AttributeCategoryCount, ...]: ...

    async def update_business_fields(self, attribute: AttributeDefinition) -> bool: ...

    async def update_status(self, attribute: AttributeDefinition) -> bool: ...

    async def delete_by_id(self, attribute_id: UUID | str) -> bool: ...


class AttributeCategoryRepository(Protocol):
    """Port implemented by adapters that expose system attribute categories."""

    async def add(self, category: AttributeCategory) -> bool: ...

    async def get_by_id(self, category_id: UUID | str) -> AttributeCategory | None: ...

    async def get_by_external_id(self, external_id: str) -> AttributeCategory | None: ...

    async def list(self, *, active_only: bool = True) -> tuple[AttributeCategory, ...]: ...

    async def update_business_fields(self, category: AttributeCategory) -> bool: ...

    async def update_status(self, category: AttributeCategory) -> bool: ...

    async def delete_by_id(self, category_id: UUID | str) -> bool: ...


class AttributeCategoryUsageRepository(Protocol):
    """Port implemented by adapters that inspect category dependencies."""

    async def get_usage(self, category_id: UUID | str) -> AttributeCategoryUsage: ...


class AttributeDefinitionUsageRepository(Protocol):
    """Port implemented by adapters that inspect attribute definition dependencies."""

    async def get_usage(self, attribute_id: UUID | str) -> AttributeDefinitionUsage: ...


class AttributeDictionaryReferenceRepository(Protocol):
    """Port implemented by adapters that resolve dictionary bindings for attributes."""

    async def get_dictionary_by_id(self, dictionary_id: UUID | str) -> Dictionary | None: ...
