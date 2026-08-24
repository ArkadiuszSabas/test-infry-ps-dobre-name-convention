"""Application ports for system catalog configuration."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from docmind_api.domain.system_catalogs.models import (
    SystemCatalogDisplayMode,
    SystemCatalogExtensionField,
)


class Clock(Protocol):
    """Port for obtaining audit timestamps."""

    def now(self) -> datetime: ...


class SystemCatalogIdFactory(Protocol):
    """Port for creating system catalog row identifiers."""

    def new_id(self) -> UUID: ...


class SystemCatalogDefinitionRepository(Protocol):
    """Port implemented by system catalog configuration persistence."""

    async def get_definition(
        self,
        system_catalog_key: str,
    ) -> tuple[tuple[SystemCatalogExtensionField, ...], tuple[SystemCatalogDisplayMode, ...]]: ...

    async def replace_definition(
        self,
        *,
        system_catalog_key: str,
        fields: tuple[SystemCatalogExtensionField, ...],
        display_modes: tuple[SystemCatalogDisplayMode, ...],
    ) -> tuple[tuple[SystemCatalogExtensionField, ...], tuple[SystemCatalogDisplayMode, ...]]: ...

    async def dictionary_exists(self, dictionary_id: UUID) -> bool: ...

    async def active_dictionary_exists(self, dictionary_id: UUID) -> bool: ...

    async def attribute_definition_exists(self, attribute_definition_id: UUID) -> bool: ...

    async def active_attribute_definition_exists(self, attribute_definition_id: UUID) -> bool: ...

    async def extension_field_has_values(self, extension_field_id: UUID) -> bool: ...

    async def active_document_types_missing_extension_value(
        self,
        extension_field_id: UUID,
    ) -> bool: ...
