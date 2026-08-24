"""Read-only custom dictionary lookup use cases."""

from uuid import UUID

from docmind_api.application.dictionaries.commands import (
    DictionaryEntryPage,
    LookupDictionaryEntriesQuery,
    ResolveDictionaryEntryQuery,
)
from docmind_api.application.dictionaries.errors import (
    DictionaryEntryNotFoundError,
    DictionaryNotFoundError,
    DictionaryValidationError,
)
from docmind_api.application.dictionaries.ports import DictionaryRepository
from docmind_api.application.dictionaries.validation import (
    normalize_search,
    validate_entry_page_window,
    validated_dictionary_reference,
)
from docmind_api.domain.dictionaries.models import (
    Dictionary,
    DictionaryEntry,
    DictionaryStatus,
    normalize_dictionary_external_id,
)


class DictionaryLookupService:
    """Application service for review-safe dictionary entry lookup."""

    def __init__(self, *, repository: DictionaryRepository) -> None:
        self._repository = repository

    async def lookup_active_entries(
        self,
        query: LookupDictionaryEntriesQuery,
    ) -> DictionaryEntryPage:
        """Return active entries that may be selected as new metadata values."""

        dictionary = await self._get_dictionary(query.dictionary_id)
        validate_entry_page_window(limit=query.limit, offset=query.offset)
        if not dictionary.is_active:
            return DictionaryEntryPage(
                entries=(),
                total_count=0,
                limit=query.limit,
                offset=query.offset,
            )

        result = await self._repository.search_entries(
            dictionary.id,
            status=DictionaryStatus.ACTIVE,
            search=normalize_search(query.search),
            limit=query.limit,
            offset=query.offset,
        )
        return DictionaryEntryPage(
            entries=result.entries,
            total_count=result.total_count,
            limit=query.limit,
            offset=query.offset,
        )

    async def resolve_entry_by_external_id(
        self,
        query: ResolveDictionaryEntryQuery,
    ) -> DictionaryEntry:
        """Resolve a stored metadata value, including inactive entries."""

        dictionary = await self._get_dictionary(query.dictionary_id)
        try:
            entry_external_id = normalize_dictionary_external_id(query.entry_external_id)
        except ValueError as error:
            raise DictionaryValidationError(message=str(error)) from error

        entry = await self._repository.get_entry_by_external_id(
            dictionary.id,
            entry_external_id,
        )
        if entry is None:
            raise DictionaryEntryNotFoundError(
                dictionary_id=dictionary.id,
                entry_id=entry_external_id,
            )
        return entry

    async def _get_dictionary(self, dictionary_id: UUID | str) -> Dictionary:
        normalized_reference = validated_dictionary_reference(dictionary_id)
        dictionary = await self._repository.get_dictionary_by_id(normalized_reference)
        if dictionary is None:
            raise DictionaryNotFoundError(dictionary_id=normalized_reference)
        return dictionary
