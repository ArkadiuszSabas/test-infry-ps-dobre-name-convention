"""Workspace registration, directory binding, and provisioning-request use cases."""

from uuid import UUID

from docmind_api.application.dictionaries.entry_workflow import with_generated_entry_values
from docmind_api.application.dictionaries.errors import (
    DictionaryEntryAlreadyExistsError,
    DictionaryEntryNotFoundError,
    DictionaryEntryValidationError,
)
from docmind_api.application.dictionaries.ports import DictionaryRepository
from docmind_api.application.dictionaries.validation import validated_entry_values
from docmind_api.application.workspaces.commands import (
    NewDirectoryEntry,
    RegisterWorkspaceCommand,
    RetryWorkspaceProvisioningCommand,
    UpdateWorkspaceDirectoryEntryCommand,
    WorkspaceDetails,
)
from docmind_api.application.workspaces.errors import (
    WorkspaceDirectoryConfigurationError,
    WorkspaceDirectoryEntryConflictError,
    WorkspaceIdempotencyConflictError,
)
from docmind_api.application.workspaces.ports import (
    Clock,
    WorkspaceDirectoryConfiguration,
    WorkspaceIdFactory,
    WorkspaceRegistrationWriteResult,
    WorkspaceRepository,
)
from docmind_api.application.workspaces.read import get_workspace_details, require_workspace
from docmind_api.application.workspaces.registration import (
    registration_fingerprint,
    require_available_configuration,
    schema_name,
    validate_registration_shape,
)
from docmind_api.application.workspaces.retry import retry_workspace_provisioning
from docmind_api.domain.dictionaries.models import (
    DictionaryEntry,
    DictionaryStatus,
    normalize_dictionary_external_id,
)
from docmind_api.domain.workspaces.models import (
    ProvisioningRequest,
    ProvisioningRequestStatus,
    Workspace,
    WorkspaceLifecycle,
    WorkspaceSchemaState,
)

_INITIAL_WORKSPACE_BASELINE_REVISION = "workspace-m1"


class WorkspaceRegistryService:
    """Application boundary for profile-configured workspace administration."""

    def __init__(
        self,
        *,
        repository: WorkspaceRepository,
        dictionary_repository: DictionaryRepository,
        configuration: WorkspaceDirectoryConfiguration,
        clock: Clock,
        id_factory: WorkspaceIdFactory,
    ) -> None:
        self._repository = repository
        self._dictionary_repository = dictionary_repository
        self._configuration = configuration
        self._clock = clock
        self._id_factory = id_factory

    async def register(self, command: RegisterWorkspaceCommand) -> WorkspaceDetails:
        """Atomically create/adopt a directory entry, workspace, and request."""

        require_available_configuration(self._configuration)
        validate_registration_shape(command)
        fingerprint = registration_fingerprint(command)
        existing_details = await self._existing_registration_details(
            idempotency_key=command.idempotency_key,
            fingerprint=fingerprint,
        )
        if existing_details is not None:
            return existing_details

        directory = await self._get_configured_directory()
        existing_details = await self._existing_registration_details(
            idempotency_key=command.idempotency_key,
            fingerprint=fingerprint,
        )
        if existing_details is not None:
            return existing_details
        new_entry = await self._new_directory_entry(
            directory_id=UUID(str(directory.id)),
            command=command.new_directory_entry,
        )
        try:
            directory_entry = new_entry or await self._adoptable_directory_entry(
                directory_id=UUID(str(directory.id)),
                entry_id=command.directory_entry_id,
            )
        except WorkspaceDirectoryEntryConflictError:
            existing_details = await self._existing_registration_details(
                idempotency_key=command.idempotency_key,
                fingerprint=fingerprint,
            )
            if existing_details is not None:
                return existing_details
            raise
        timestamp = self._clock.now()
        workspace_id = self._id_factory.new_id()
        workspace = Workspace(
            id=workspace_id,
            directory_dictionary_id=UUID(str(directory.id)),
            directory_entry_id=UUID(str(directory_entry.id)),
            schema_name=schema_name(workspace_id),
            schema_layout="dedicated_schema",
            storage_prefix=f"workspaces/{workspace_id}",
            lifecycle=WorkspaceLifecycle.REGISTERED,
            schema_state=WorkspaceSchemaState.PENDING,
            schema_revision=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        request = ProvisioningRequest(
            id=self._id_factory.new_id(),
            workspace_id=workspace_id,
            idempotency_key=command.idempotency_key,
            payload_fingerprint=fingerprint,
            target_revision=_INITIAL_WORKSPACE_BASELINE_REVISION,
            status=ProvisioningRequestStatus.PENDING,
            result_code=None,
            result_message=None,
            created_at=timestamp,
            updated_at=timestamp,
            completed_at=None,
        )
        write_result = await self._repository.create_registration(
            directory_entry=new_entry,
            workspace=workspace,
            request=request,
        )
        if write_result is WorkspaceRegistrationWriteResult.CREATED:
            if new_entry is not None:
                await self._dictionary_repository.update_dictionary_versions(
                    directory.bump_entries_version(updated_at=timestamp),
                )
            return await self.get_details(workspace.id)

        existing_details = await self._existing_registration_details(
            idempotency_key=command.idempotency_key,
            fingerprint=fingerprint,
        )
        if existing_details is not None:
            return existing_details
        if write_result is WorkspaceRegistrationWriteResult.DIRECTORY_ENTRY_BOUND:
            raise WorkspaceDirectoryEntryConflictError(directory_entry_id=directory_entry.id)
        raise DictionaryEntryAlreadyExistsError(
            dictionary_id=directory.id,
            external_id=directory_entry.external_id,
        )

    async def list_details(self) -> tuple[WorkspaceDetails, ...]:
        """Return registered workspaces without exposing unbound dictionary data."""

        require_available_configuration(self._configuration)
        workspaces = await self._repository.list_workspaces()
        details: list[WorkspaceDetails] = []
        for workspace in workspaces:
            details.append(await self.get_details(workspace.id))
        return tuple(details)

    async def get_details(self, workspace_id: UUID) -> WorkspaceDetails:
        """Return technical state, directory display data, and durable requests."""

        require_available_configuration(self._configuration)
        return await get_workspace_details(
            repository=self._repository,
            dictionary_repository=self._dictionary_repository,
            workspace_id=workspace_id,
        )

    async def update_directory_entry(
        self,
        command: UpdateWorkspaceDirectoryEntryCommand,
    ) -> WorkspaceDetails:
        """Change business-only directory fields without touching workspace identity."""

        require_available_configuration(self._configuration)
        workspace = await require_workspace(
            repository=self._repository,
            workspace_id=command.workspace_id,
        )
        if workspace.directory_entry_id is None:
            raise WorkspaceDirectoryConfigurationError()
        dictionary = await self._dictionary_repository.get_dictionary_by_id_for_update(
            workspace.directory_dictionary_id or workspace.directory_entry_id,
        )
        if dictionary is None:
            raise WorkspaceDirectoryConfigurationError()
        entry = await self._dictionary_repository.get_entry_by_id_for_update(
            dictionary.id,
            workspace.directory_entry_id,
        )
        if entry is None:
            raise WorkspaceDirectoryConfigurationError()
        fields = await self._dictionary_repository.list_fields(
            entry.dictionary_id,
            status=DictionaryStatus.ACTIVE,
        )
        entries = (
            await self._dictionary_repository.search_entries(
                entry.dictionary_id,
                status=None,
                limit=0,
                offset=0,
            )
        ).entries
        external_id = command.external_id if command.external_id is not None else entry.external_id
        if command.external_id is not None:
            try:
                external_id = normalize_dictionary_external_id(command.external_id)
            except ValueError as error:
                raise DictionaryEntryValidationError(message=str(error)) from error
            duplicate = await self._dictionary_repository.get_entry_by_external_id(
                entry.dictionary_id,
                external_id,
            )
            if duplicate is not None and duplicate.id != entry.id:
                raise DictionaryEntryAlreadyExistsError(
                    dictionary_id=entry.dictionary_id,
                    external_id=external_id,
                )
        values = command.values if command.values is not None else dict(entry.values)
        validated_values = validated_entry_values(
            fields=fields,
            values=values,
            existing_entries=entries,
            current_entry_id=UUID(str(entry.id)),
        )
        try:
            updated = entry.update_business_fields(
                external_id=external_id,
                label=command.label if command.label is not None else entry.label,
                values=validated_values,
                sort_order=command.sort_order
                if command.sort_order is not None
                else entry.sort_order,
                updated_at=self._clock.now(),
            )
        except ValueError as error:
            raise DictionaryEntryValidationError(message=str(error)) from error
        if not await self._dictionary_repository.update_entry_business_fields(updated):
            raise DictionaryEntryNotFoundError(
                dictionary_id=entry.dictionary_id,
                entry_id=entry.id,
            )
        await self._dictionary_repository.update_dictionary_versions(
            dictionary.bump_entries_version(updated_at=updated.updated_at),
        )
        return await self.get_details(workspace.id)

    async def retry_provisioning(
        self,
        command: RetryWorkspaceProvisioningCommand,
    ) -> WorkspaceDetails:
        """Delegate durable retry orchestration while retaining the service boundary."""

        return await retry_workspace_provisioning(
            repository=self._repository,
            configuration=self._configuration,
            clock=self._clock,
            id_factory=self._id_factory,
            get_details=self.get_details,
            command=command,
        )

    async def _existing_registration_details(
        self,
        *,
        idempotency_key: str,
        fingerprint: str,
    ) -> WorkspaceDetails | None:
        existing_request = await self._repository.get_request_by_idempotency_key(
            idempotency_key,
        )
        if existing_request is None:
            return None
        if existing_request.payload_fingerprint != fingerprint:
            raise WorkspaceIdempotencyConflictError(idempotency_key=idempotency_key)
        return await self.get_details(existing_request.workspace_id)

    async def _get_configured_directory(self):
        dictionary = await self._dictionary_repository.get_dictionary_by_external_id_for_update(
            self._configuration.dictionary_external_id or "",
        )
        if dictionary is None or dictionary.status is not DictionaryStatus.ACTIVE:
            raise WorkspaceDirectoryConfigurationError()
        return dictionary

    async def _new_directory_entry(
        self,
        *,
        directory_id: UUID,
        command: NewDirectoryEntry | None,
    ) -> DictionaryEntry | None:
        if command is None:
            return None
        fields = await self._dictionary_repository.list_fields(
            directory_id,
            status=DictionaryStatus.ACTIVE,
        )
        existing_entries = (
            await self._dictionary_repository.search_entries(
                directory_id,
                status=None,
                limit=0,
                offset=0,
            )
        ).entries
        normalized_values = validated_entry_values(
            fields=fields,
            values=with_generated_entry_values(
                fields=fields,
                values=command.values,
                existing_entries=existing_entries,
            ),
            existing_entries=existing_entries,
        )
        timestamp = self._clock.now()
        try:
            return DictionaryEntry(
                id=self._id_factory.new_id(),
                dictionary_id=directory_id,
                external_id=command.external_id,
                label=command.label,
                values=normalized_values,
                status=DictionaryStatus.ACTIVE,
                sort_order=command.sort_order,
                created_at=timestamp,
                updated_at=timestamp,
            )
        except ValueError as error:
            raise DictionaryEntryValidationError(message=str(error)) from error

    async def _adoptable_directory_entry(
        self,
        *,
        directory_id: UUID,
        entry_id: UUID | None,
    ) -> DictionaryEntry:
        if entry_id is None:
            raise WorkspaceDirectoryConfigurationError()
        entry = await self._dictionary_repository.get_entry_by_id_for_update(
            directory_id,
            entry_id,
        )
        if entry is None or entry.status is not DictionaryStatus.ACTIVE:
            raise WorkspaceDirectoryConfigurationError()
        if await self._repository.get_workspace_by_directory_entry_id(entry_id):
            raise WorkspaceDirectoryEntryConflictError(directory_entry_id=entry_id)
        return entry
