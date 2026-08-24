"""Custom dictionary application use cases."""

from uuid import UUID, uuid4

from docmind_api.application.dictionaries.commands import (
    CreateDictionaryCommand,
    CreateDictionaryEntryCommand,
    DeactivateDictionaryCommand,
    DeactivateDictionaryEntryCommand,
    DeleteDictionaryCommand,
    DeleteDictionaryEntryCommand,
    DeleteDictionaryEntryResult,
    DeleteDictionaryResult,
    DictionaryEntryPage,
    ListDictionariesQuery,
    ListDictionaryEntriesQuery,
    SaveDictionaryFieldsCommand,
    UpdateDictionaryCommand,
    UpdateDictionaryEntryCommand,
)
from docmind_api.application.dictionaries.entry_workflow import (
    DictionaryEntryCatalogWorkflow,
)
from docmind_api.application.dictionaries.errors import (
    DictionaryAlreadyExistsError,
    DictionaryFieldsInUseError,
    DictionaryInUseError,
    DictionaryNotFoundError,
    DictionaryUsedByActiveAttributeError,
    DictionaryUsedByActiveSystemCatalogFieldError,
    DictionaryValidationError,
)
from docmind_api.application.dictionaries.field_factory import build_dictionary_field
from docmind_api.application.dictionaries.ports import (
    Clock,
    DictionaryEntryIdFactory,
    DictionaryFieldIdFactory,
    DictionaryIdFactory,
    DictionaryRepository,
    DictionaryUsageRepository,
)
from docmind_api.application.dictionaries.validation import (
    dictionary_status_filter,
    duplicate_field_ids,
    normalize_search,
    require_active_dictionary,
    resolve_update,
    validated_dictionary_reference,
)
from docmind_api.domain.dictionaries.models import (
    Dictionary,
    DictionaryEntry,
    DictionaryField,
    DictionaryStatus,
    normalize_dictionary_external_id,
)


class DictionaryCatalogService:
    """Application service for custom dictionary workflows."""

    def __init__(
        self,
        *,
        repository: DictionaryRepository,
        usage_repository: DictionaryUsageRepository,
        clock: Clock,
        dictionary_id_factory: DictionaryIdFactory | None = None,
        field_id_factory: DictionaryFieldIdFactory | None = None,
        entry_id_factory: DictionaryEntryIdFactory | None = None,
    ) -> None:
        self._repository = repository
        self._usage_repository = usage_repository
        self._clock = clock
        self._dictionary_id_factory = dictionary_id_factory
        self._field_id_factory = field_id_factory
        self._entry_workflow = DictionaryEntryCatalogWorkflow(
            repository=repository,
            usage_repository=usage_repository,
            clock=clock,
            entry_id_factory=entry_id_factory,
        )

    async def create_dictionary(self, command: CreateDictionaryCommand) -> Dictionary:
        timestamp = self._clock.now()
        try:
            external_id = normalize_dictionary_external_id(command.external_id)
            dictionary = Dictionary(
                id=(
                    self._dictionary_id_factory.new_id()
                    if self._dictionary_id_factory is not None
                    else uuid4()
                ),
                external_id=external_id,
                name=command.name,
                description=command.description,
                status=DictionaryStatus.ACTIVE,
                schema_version=1,
                entries_version=1,
                created_at=timestamp,
                updated_at=timestamp,
            )
        except ValueError as error:
            raise DictionaryValidationError(message=str(error)) from error

        if await self._repository.get_dictionary_by_external_id(dictionary.external_id):
            raise DictionaryAlreadyExistsError(external_id=dictionary.external_id)
        created = await self._repository.add_dictionary(dictionary)
        if not created:
            raise DictionaryAlreadyExistsError(external_id=dictionary.external_id)

        return dictionary

    async def list_dictionaries(
        self,
        query: ListDictionariesQuery,
    ) -> tuple[Dictionary, ...]:
        return await self._repository.list_dictionaries(
            status=dictionary_status_filter(query.status),
            search=normalize_search(query.search),
        )

    async def update_dictionary(self, command: UpdateDictionaryCommand) -> Dictionary:
        dictionary = await self._get_dictionary(command.dictionary_id)
        try:
            updated = dictionary.update_business_fields(
                name=resolve_update(command.name, dictionary.name),
                description=resolve_update(command.description, dictionary.description),
                updated_at=self._clock.now(),
            )
        except ValueError as error:
            raise DictionaryValidationError(message=str(error)) from error

        if not await self._repository.update_dictionary_business_fields(updated):
            raise DictionaryNotFoundError(dictionary_id=dictionary.id)
        return updated

    async def deactivate_dictionary(
        self,
        command: DeactivateDictionaryCommand,
    ) -> Dictionary:
        dictionary = await self._get_dictionary(command.dictionary_id)
        usage = await self._usage_repository.get_usage(dictionary.id)
        if usage.active_attribute_bindings:
            raise DictionaryUsedByActiveAttributeError(
                dictionary_id=dictionary.id,
                usage=usage,
            )
        if usage.active_system_catalog_fields:
            raise DictionaryUsedByActiveSystemCatalogFieldError(
                dictionary_id=dictionary.id,
                usage=usage,
            )

        deactivated = dictionary.deactivate(updated_at=self._clock.now())
        if not await self._repository.update_dictionary_status(deactivated):
            raise DictionaryNotFoundError(dictionary_id=dictionary.id)
        return deactivated

    async def delete_dictionary(
        self,
        command: DeleteDictionaryCommand,
    ) -> DeleteDictionaryResult:
        dictionary = await self._get_dictionary(command.dictionary_id)
        usage = await self._usage_repository.get_usage(dictionary.id)
        if usage.has_blocking_dependencies:
            raise DictionaryInUseError(dictionary_id=dictionary.id, usage=usage)
        if not await self._repository.delete_dictionary_by_id(dictionary.id):
            raise DictionaryNotFoundError(dictionary_id=dictionary.id)

        return DeleteDictionaryResult(dictionary_id=UUID(str(dictionary.id)), deleted=True)

    async def list_fields(self, *, dictionary_id: UUID | str) -> tuple[DictionaryField, ...]:
        dictionary = await self._get_dictionary(dictionary_id)
        return await self._repository.list_fields(dictionary.id)

    async def save_fields(
        self,
        command: SaveDictionaryFieldsCommand,
    ) -> tuple[DictionaryField, ...]:
        dictionary = await self._get_dictionary(command.dictionary_id)
        require_active_dictionary(dictionary)
        timestamp = self._clock.now()
        try:
            field_ids = duplicate_field_ids(command.fields)
        except ValueError as error:
            raise DictionaryValidationError(message=str(error)) from error
        if field_ids:
            raise DictionaryValidationError(
                message="Dictionary field payload cannot contain duplicate external IDs.",
                details={"duplicate_field_external_ids": field_ids},
            )

        existing_fields = {
            field.external_id: field for field in await self._repository.list_fields(dictionary.id)
        }
        submitted_field_external_ids = {
            normalize_dictionary_external_id(item.external_id) for item in command.fields
        }
        removed_field_external_ids = tuple(
            sorted(
                external_id
                for external_id in existing_fields
                if external_id not in submitted_field_external_ids
            ),
        )
        if removed_field_external_ids:
            usage = await self._usage_repository.get_usage(dictionary.id)
            if usage.entries > 0:
                raise DictionaryFieldsInUseError(
                    dictionary_id=dictionary.id,
                    removed_field_external_ids=removed_field_external_ids,
                    usage=usage,
                )
        try:
            fields = tuple(
                build_dictionary_field(
                    item=item,
                    dictionary=dictionary,
                    existing_fields=existing_fields,
                    timestamp=timestamp,
                    field_id_factory=self._field_id_factory,
                )
                for item in command.fields
            )
        except ValueError as error:
            raise DictionaryValidationError(message=str(error)) from error

        await self._entry_workflow.validate_existing_entries_against_fields(
            dictionary_id=UUID(str(dictionary.id)),
            fields=fields,
        )
        await self._repository.replace_fields(dictionary.id, fields)
        bumped_dictionary = dictionary.bump_schema_version(updated_at=timestamp)
        await self._repository.update_dictionary_versions(bumped_dictionary)
        return await self._repository.list_fields(dictionary.id)

    async def create_entry(
        self,
        command: CreateDictionaryEntryCommand,
    ) -> DictionaryEntry:
        return await self._entry_workflow.create_entry(command)

    async def list_entries(self, query: ListDictionaryEntriesQuery) -> DictionaryEntryPage:
        return await self._entry_workflow.list_entries(query)

    async def update_entry(self, command: UpdateDictionaryEntryCommand) -> DictionaryEntry:
        return await self._entry_workflow.update_entry(command)

    async def deactivate_entry(
        self,
        command: DeactivateDictionaryEntryCommand,
    ) -> DictionaryEntry:
        return await self._entry_workflow.deactivate_entry(command)

    async def delete_entry(
        self,
        command: DeleteDictionaryEntryCommand,
    ) -> DeleteDictionaryEntryResult:
        return await self._entry_workflow.delete_entry(command)

    async def _get_dictionary(self, dictionary_id: UUID | str) -> Dictionary:
        normalized_reference = validated_dictionary_reference(dictionary_id)
        dictionary = await self._repository.get_dictionary_by_id(normalized_reference)
        if dictionary is None:
            raise DictionaryNotFoundError(dictionary_id=normalized_reference)
        return dictionary
