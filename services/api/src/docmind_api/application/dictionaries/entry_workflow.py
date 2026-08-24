"""Custom dictionary entry application workflows."""

from collections.abc import Mapping
from uuid import UUID, uuid4

from docmind_api.application.dictionaries.commands import (
    CreateDictionaryEntryCommand,
    DeactivateDictionaryEntryCommand,
    DeleteDictionaryEntryCommand,
    DeleteDictionaryEntryResult,
    DictionaryEntryPage,
    ListDictionaryEntriesQuery,
    UpdateDictionaryEntryCommand,
)
from docmind_api.application.dictionaries.errors import (
    DictionaryEntryAlreadyExistsError,
    DictionaryEntryInUseError,
    DictionaryEntryNotFoundError,
    DictionaryEntryValidationError,
    DictionaryNotFoundError,
)
from docmind_api.application.dictionaries.ports import (
    Clock,
    DictionaryEntryIdFactory,
    DictionaryRepository,
    DictionaryUsageRepository,
)
from docmind_api.application.dictionaries.validation import (
    entry_status_filter,
    normalize_search,
    require_active_dictionary,
    resolve_update,
    validate_entry_page_window,
    validated_dictionary_reference,
    validated_entry_values,
)
from docmind_api.domain.attributes.models import AttributeDataType
from docmind_api.domain.dictionaries.models import (
    Dictionary,
    DictionaryEntry,
    DictionaryEntryScalar,
    DictionaryField,
    DictionaryStatus,
    normalize_dictionary_external_id,
)


class DictionaryEntryCatalogWorkflow:
    """Application workflow for custom dictionary entries."""

    def __init__(
        self,
        *,
        repository: DictionaryRepository,
        usage_repository: DictionaryUsageRepository,
        clock: Clock,
        entry_id_factory: DictionaryEntryIdFactory | None = None,
    ) -> None:
        self._repository = repository
        self._usage_repository = usage_repository
        self._clock = clock
        self._entry_id_factory = entry_id_factory

    async def create_entry(
        self,
        command: CreateDictionaryEntryCommand,
    ) -> DictionaryEntry:
        dictionary = await self._get_dictionary(command.dictionary_id)
        require_active_dictionary(dictionary)
        try:
            external_id = normalize_dictionary_external_id(command.external_id)
        except ValueError as error:
            raise DictionaryEntryValidationError(message=str(error)) from error
        if await self._repository.get_entry_by_external_id(dictionary.id, external_id):
            raise DictionaryEntryAlreadyExistsError(
                dictionary_id=dictionary.id,
                external_id=external_id,
            )

        fields = await self._repository.list_fields(
            dictionary.id,
            status=DictionaryStatus.ACTIVE,
        )
        existing_entries = await self._existing_entries_for_unique_validation(
            dictionary_id=UUID(str(dictionary.id)),
            fields=fields,
            include_for_generated_values=True,
        )
        values = _with_generated_entry_values(
            fields=fields,
            values=command.values,
            existing_entries=existing_entries,
        )
        normalized_values = validated_entry_values(
            fields=fields,
            values=values,
            existing_entries=existing_entries,
        )
        timestamp = self._clock.now()
        try:
            entry = DictionaryEntry(
                id=(
                    self._entry_id_factory.new_id()
                    if self._entry_id_factory is not None
                    else uuid4()
                ),
                dictionary_id=dictionary.id,
                external_id=external_id,
                label=command.label,
                values=normalized_values,
                status=DictionaryStatus.ACTIVE,
                sort_order=command.sort_order,
                created_at=timestamp,
                updated_at=timestamp,
            )
        except ValueError as error:
            raise DictionaryEntryValidationError(message=str(error)) from error

        if not await self._repository.add_entry(entry):
            raise DictionaryEntryAlreadyExistsError(
                dictionary_id=dictionary.id,
                external_id=entry.external_id,
            )
        await self._repository.update_dictionary_versions(
            dictionary.bump_entries_version(updated_at=timestamp),
        )
        return entry

    async def list_entries(self, query: ListDictionaryEntriesQuery) -> DictionaryEntryPage:
        dictionary = await self._get_dictionary(query.dictionary_id)
        validate_entry_page_window(limit=query.limit, offset=query.offset)
        result = await self._repository.search_entries(
            dictionary.id,
            status=entry_status_filter(query.status),
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

    async def update_entry(self, command: UpdateDictionaryEntryCommand) -> DictionaryEntry:
        dictionary = await self._get_dictionary(command.dictionary_id)
        require_active_dictionary(dictionary)
        existing = await self._repository.get_entry_by_id(dictionary.id, command.entry_id)
        if existing is None:
            raise DictionaryEntryNotFoundError(
                dictionary_id=dictionary.id,
                entry_id=command.entry_id,
            )

        fields = await self._repository.list_fields(
            dictionary.id,
            status=DictionaryStatus.ACTIVE,
        )
        existing_entries = await self._existing_entries_for_unique_validation(
            dictionary_id=UUID(str(dictionary.id)),
            fields=fields,
        )
        values = resolve_update(command.values, dict(existing.values))
        normalized_values = validated_entry_values(
            fields=fields,
            values=values,
            existing_entries=existing_entries,
            current_entry_id=UUID(str(existing.id)),
        )
        timestamp = self._clock.now()
        try:
            updated = existing.update_business_fields(
                external_id=resolve_update(command.external_id, existing.external_id),
                label=resolve_update(command.label, existing.label),
                values=normalized_values,
                sort_order=resolve_update(command.sort_order, existing.sort_order),
                updated_at=timestamp,
            )
        except ValueError as error:
            raise DictionaryEntryValidationError(message=str(error)) from error

        if updated.external_id != existing.external_id:
            duplicate = await self._repository.get_entry_by_external_id(
                dictionary.id,
                updated.external_id,
            )
            if duplicate is not None and duplicate.id != existing.id:
                raise DictionaryEntryAlreadyExistsError(
                    dictionary_id=dictionary.id,
                    external_id=updated.external_id,
                )

        if not await self._repository.update_entry_business_fields(updated):
            raise DictionaryEntryNotFoundError(dictionary_id=dictionary.id, entry_id=existing.id)
        await self._repository.update_dictionary_versions(
            dictionary.bump_entries_version(updated_at=timestamp),
        )
        return updated

    async def deactivate_entry(
        self,
        command: DeactivateDictionaryEntryCommand,
    ) -> DictionaryEntry:
        dictionary = await self._get_dictionary(command.dictionary_id)
        existing = await self._repository.get_entry_by_id(dictionary.id, command.entry_id)
        if existing is None:
            raise DictionaryEntryNotFoundError(
                dictionary_id=dictionary.id,
                entry_id=command.entry_id,
            )
        timestamp = self._clock.now()
        deactivated = existing.deactivate(updated_at=timestamp)
        if not await self._repository.update_entry_status(deactivated):
            raise DictionaryEntryNotFoundError(dictionary_id=dictionary.id, entry_id=existing.id)
        await self._repository.update_dictionary_versions(
            dictionary.bump_entries_version(updated_at=timestamp),
        )
        return deactivated

    async def delete_entry(
        self,
        command: DeleteDictionaryEntryCommand,
    ) -> DeleteDictionaryEntryResult:
        dictionary = await self._get_dictionary(command.dictionary_id)
        existing = await self._repository.get_entry_by_id(dictionary.id, command.entry_id)
        if existing is None:
            raise DictionaryEntryNotFoundError(
                dictionary_id=dictionary.id,
                entry_id=command.entry_id,
            )
        timestamp = self._clock.now()
        usage = await self._usage_repository.get_entry_usage(
            dictionary.id,
            existing.external_id,
        )
        if usage.has_blocking_dependencies:
            raise DictionaryEntryInUseError(
                dictionary_id=dictionary.id,
                entry_id=existing.id,
                usage=usage,
            )
        if not await self._repository.delete_entry_by_id(dictionary.id, existing.id):
            raise DictionaryEntryNotFoundError(dictionary_id=dictionary.id, entry_id=existing.id)
        await self._repository.update_dictionary_versions(
            dictionary.bump_entries_version(updated_at=timestamp),
        )
        return DeleteDictionaryEntryResult(entry_id=UUID(str(existing.id)), deleted=True)

    async def validate_existing_entries_against_fields(
        self,
        *,
        dictionary_id: UUID,
        fields: tuple[DictionaryField, ...],
    ) -> None:
        entries = (
            await self._repository.search_entries(
                dictionary_id,
                status=None,
                limit=0,
                offset=0,
            )
        ).entries
        for entry in entries:
            validated_entry_values(
                fields=fields,
                values=dict(entry.values),
                existing_entries=entries,
                current_entry_id=UUID(str(entry.id)),
            )

    async def _get_dictionary(self, dictionary_id: UUID | str) -> Dictionary:
        normalized_reference = validated_dictionary_reference(dictionary_id)
        dictionary = await self._repository.get_dictionary_by_id(normalized_reference)
        if dictionary is None:
            raise DictionaryNotFoundError(dictionary_id=normalized_reference)
        return dictionary

    async def _existing_entries_for_unique_validation(
        self,
        *,
        dictionary_id: UUID,
        fields: tuple[DictionaryField, ...],
        include_for_generated_values: bool = False,
    ) -> tuple[DictionaryEntry, ...]:
        has_unique_field = any(field.is_unique for field in fields)
        has_generated_numeric_field = any(
            _is_auto_generated_numeric_identifier(field) for field in fields
        )
        if not has_unique_field and not (
            include_for_generated_values and has_generated_numeric_field
        ):
            return ()
        return (
            await self._repository.search_entries(
                dictionary_id,
                status=None,
                limit=0,
                offset=0,
            )
        ).entries


def _with_generated_entry_values(
    *,
    fields: tuple[DictionaryField, ...],
    values: Mapping[str, DictionaryEntryScalar],
    existing_entries: tuple[DictionaryEntry, ...],
) -> dict[str, DictionaryEntryScalar]:
    next_values = dict(values)
    for field in fields:
        if field.format.get("generation") != "auto":
            continue
        if field.format.get("semantic_type") == "uuid":
            next_values[field.external_id] = str(uuid4())
            continue
        if field.format.get("semantic_type") == "numeric_identifier":
            next_values[field.external_id] = _next_numeric_identifier(
                field=field,
                entries=existing_entries,
            )
    return next_values


def _is_auto_generated_numeric_identifier(field: DictionaryField) -> bool:
    return (
        field.data_type == AttributeDataType.INTEGER
        and field.format.get("generation") == "auto"
        and field.format.get("semantic_type") == "numeric_identifier"
    )


def _next_numeric_identifier(
    *,
    field: DictionaryField,
    entries: tuple[DictionaryEntry, ...],
) -> int:
    max_value = 0
    for entry in entries:
        value = entry.values.get(field.external_id)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            max_value = max(max_value, value)
    return max_value + 1
