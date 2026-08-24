"""Application ports for the document type catalog."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from docmind_api.domain.document_types.models import DocumentType, DocumentTypeUsage
from docmind_api.domain.system_catalogs.models import (
    DocumentTypeExtensionValue,
    SystemCatalogExtensionField,
    SystemCatalogExtensionValueType,
)


class Clock(Protocol):
    """Port for obtaining audit timestamps."""

    def now(self) -> datetime: ...


class DocumentTypeIdFactory(Protocol):
    """Port for creating document type identifiers."""

    def new_id(self) -> UUID: ...


class DocumentTypeExtensionValueIdFactory(Protocol):
    """Port for creating document type extension value identifiers."""

    def new_id(self) -> UUID: ...


class DocumentTypeCatalogRepository(Protocol):
    """Port implemented by document type catalog persistence adapters."""

    async def add(self, document_type: DocumentType) -> bool: ...

    async def get_by_id(self, document_type_id: UUID | str) -> DocumentType | None: ...

    async def get_by_external_id(self, external_id: str) -> DocumentType | None: ...

    async def find_active_by_name_and_parameters(
        self,
        *,
        name: str,
        parameters: Mapping[str, str],
    ) -> tuple[DocumentType, ...]: ...

    async def list_active(self) -> tuple[DocumentType, ...]: ...

    async def list_all(self) -> tuple[DocumentType, ...]: ...

    async def update_business_fields(self, document_type: DocumentType) -> bool: ...

    async def update_status(self, document_type: DocumentType) -> bool: ...

    async def delete_by_id(self, document_type_id: UUID | str) -> bool: ...


class DocumentTypeUsageRepository(Protocol):
    """Port implemented by adapters that inspect document type dependencies."""

    async def get_usage(self, document_type_id: UUID | str) -> DocumentTypeUsage: ...


@dataclass(frozen=True, slots=True)
class DocumentTypeExtensionValuePayload:
    """Submitted dynamic extension value for a document type."""

    extension_field_id: UUID | str
    dictionary_entry_id: UUID | str | None = None
    text_value: str | None = None


@dataclass(frozen=True, slots=True)
class DocumentTypeExtensionValueReadModel:
    """Read model for one dynamic document type extension value."""

    extension_field_id: UUID
    code: str
    label: str
    value_type: SystemCatalogExtensionValueType
    dictionary_id: UUID | None
    dictionary_entry_id: UUID | None
    text_value: str | None
    display_value: str | None
    show_in_overview: bool
    field_order: int


@dataclass(frozen=True, slots=True)
class DocumentTypeOverviewParameter:
    """Overview parameter generated from one overview-enabled extension field."""

    code: str
    label: str
    value: str | None


@dataclass(frozen=True, slots=True)
class DocumentTypeReadModel:
    """Document type catalog item enriched with dynamic extension values."""

    document_type: DocumentType
    display_label: str
    extension_values: tuple[DocumentTypeExtensionValueReadModel, ...]
    parameters: tuple[DocumentTypeOverviewParameter, ...]
    display_mode_id: UUID | None
    sort_key: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SystemCatalogOptionReadModel:
    """Unified dropdown option for a system catalog item."""

    id: UUID
    label: str
    name: str
    extension_values: tuple[DocumentTypeExtensionValueReadModel, ...]
    parameters: tuple[DocumentTypeOverviewParameter, ...]
    display_mode_id: UUID | None


class DocumentTypeExtensionValueLookup(Protocol):
    """Port for extension value validation lookups."""

    async def active_dictionary_entry_belongs_to_active_dictionary(
        self,
        *,
        entry_id: UUID,
        dictionary_id: UUID,
    ) -> bool: ...


class DocumentTypeExtensionValueRepository(Protocol):
    """Port implemented by document type extension value persistence."""

    async def active_extension_fields(
        self,
        system_catalog_key: str,
    ) -> tuple[SystemCatalogExtensionField, ...]: ...

    async def active_dictionary_entry_belongs_to_active_dictionary(
        self,
        *,
        entry_id: UUID,
        dictionary_id: UUID,
    ) -> bool: ...

    async def replace_values(
        self,
        *,
        document_type_id: UUID,
        values: tuple[DocumentTypeExtensionValue, ...],
    ) -> None: ...

    async def build_read_models(
        self,
        document_types: tuple[DocumentType, ...],
    ) -> tuple[DocumentTypeReadModel, ...]: ...
