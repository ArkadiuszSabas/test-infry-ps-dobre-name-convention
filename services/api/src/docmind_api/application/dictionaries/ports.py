"""Application ports for custom dictionary workflows."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from docmind_api.domain.dictionaries.models import (
    Dictionary,
    DictionaryEntry,
    DictionaryEntryUsage,
    DictionaryField,
    DictionaryStatus,
    DictionaryUsage,
)


@dataclass(frozen=True, slots=True)
class DictionaryEntrySearchResult:
    """Paged dictionary entry lookup result from persistence."""

    entries: tuple[DictionaryEntry, ...]
    total_count: int


class Clock(Protocol):
    """Port for obtaining audit timestamps."""

    def now(self) -> datetime: ...


class DictionaryIdFactory(Protocol):
    """Port for creating dictionary identifiers."""

    def new_id(self) -> UUID: ...


class DictionaryFieldIdFactory(Protocol):
    """Port for creating dictionary field identifiers."""

    def new_id(self) -> UUID: ...


class DictionaryEntryIdFactory(Protocol):
    """Port for creating dictionary entry identifiers."""

    def new_id(self) -> UUID: ...


class DictionaryRepository(Protocol):
    """Port implemented by custom dictionary persistence adapters."""

    async def add_dictionary(self, dictionary: Dictionary) -> bool: ...

    async def get_dictionary_by_id(self, dictionary_id: UUID | str) -> Dictionary | None: ...

    async def get_dictionary_by_external_id(self, external_id: str) -> Dictionary | None: ...

    async def list_dictionaries(
        self,
        *,
        status: DictionaryStatus | None = None,
        search: str | None = None,
    ) -> tuple[Dictionary, ...]: ...

    async def update_dictionary_business_fields(self, dictionary: Dictionary) -> bool: ...

    async def update_dictionary_status(self, dictionary: Dictionary) -> bool: ...

    async def update_dictionary_versions(self, dictionary: Dictionary) -> bool: ...

    async def delete_dictionary_by_id(self, dictionary_id: UUID | str) -> bool: ...

    async def list_fields(
        self,
        dictionary_id: UUID | str,
        *,
        status: DictionaryStatus | None = None,
    ) -> tuple[DictionaryField, ...]: ...

    async def replace_fields(
        self,
        dictionary_id: UUID | str,
        fields: tuple[DictionaryField, ...],
    ) -> None: ...

    async def add_entry(self, entry: DictionaryEntry) -> bool: ...

    async def get_entry_by_id(
        self,
        dictionary_id: UUID | str,
        entry_id: UUID | str,
    ) -> DictionaryEntry | None: ...

    async def get_entry_by_external_id(
        self,
        dictionary_id: UUID | str,
        external_id: str,
    ) -> DictionaryEntry | None: ...

    async def search_entries(
        self,
        dictionary_id: UUID | str,
        *,
        status: DictionaryStatus | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DictionaryEntrySearchResult: ...

    async def update_entry_business_fields(self, entry: DictionaryEntry) -> bool: ...

    async def update_entry_status(self, entry: DictionaryEntry) -> bool: ...

    async def delete_entry_by_id(
        self,
        dictionary_id: UUID | str,
        entry_id: UUID | str,
    ) -> bool: ...


class DictionaryUsageRepository(Protocol):
    """Port implemented by adapters that inspect dictionary dependencies."""

    async def get_usage(self, dictionary_id: UUID | str) -> DictionaryUsage: ...

    async def get_entry_usage(
        self,
        dictionary_id: UUID | str,
        entry_external_id: str,
    ) -> DictionaryEntryUsage: ...
