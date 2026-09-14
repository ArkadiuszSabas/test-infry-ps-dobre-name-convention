"""SQLAlchemy repositories for shared workspace registry records."""

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.workspaces.ports import (
    WorkspaceRegistrationWriteResult,
)
from docmind_api.domain.dictionaries.models import DictionaryEntry
from docmind_api.domain.workspaces.models import ProvisioningRequest, Workspace
from docmind_api.infrastructure.persistence.dictionaries.tables import dictionary_entries_table
from docmind_api.infrastructure.persistence.workspaces.mappers import (
    provisioning_request_from_row,
    workspace_from_row,
)
from docmind_api.infrastructure.persistence.workspaces.tables import (
    workspace_provisioning_requests_table,
    workspaces_table,
)


class SqlAlchemyWorkspaceRepository:
    """PostgreSQL-backed workspace registry repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return await self._get_workspace(workspace_id)

    async def get_workspace_for_update(self, workspace_id: UUID) -> Workspace | None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:workspace_id))"),
            {"workspace_id": str(workspace_id)},
        )
        return await self._get_workspace(workspace_id)

    async def _get_workspace(
        self,
        workspace_id: UUID,
        *,
        for_update: bool = False,
    ) -> Workspace | None:
        statement = select(workspaces_table).where(workspaces_table.c.id == workspace_id)
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        row = result.mappings().one_or_none()
        return workspace_from_row(row) if row is not None else None

    async def list_workspaces(self) -> tuple[Workspace, ...]:
        result = await self._session.execute(
            select(workspaces_table).order_by(
                workspaces_table.c.created_at.desc(), workspaces_table.c.id
            ),
        )
        return tuple(workspace_from_row(row) for row in result.mappings())

    async def get_workspace_by_directory_entry_id(
        self,
        directory_entry_id: UUID,
    ) -> Workspace | None:
        result = await self._session.execute(
            select(workspaces_table).where(
                workspaces_table.c.directory_entry_id == directory_entry_id,
            ),
        )
        row = result.mappings().one_or_none()
        return workspace_from_row(row) if row is not None else None

    async def list_requests(self, workspace_id: UUID) -> tuple[ProvisioningRequest, ...]:
        result = await self._session.execute(
            select(workspace_provisioning_requests_table)
            .where(workspace_provisioning_requests_table.c.workspace_id == workspace_id)
            .order_by(
                workspace_provisioning_requests_table.c.created_at.desc(),
                workspace_provisioning_requests_table.c.id.desc(),
            ),
        )
        return tuple(provisioning_request_from_row(row) for row in result.mappings())

    async def get_request_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> ProvisioningRequest | None:
        result = await self._session.execute(
            select(workspace_provisioning_requests_table).where(
                workspace_provisioning_requests_table.c.idempotency_key == idempotency_key,
            ),
        )
        row = result.mappings().one_or_none()
        return provisioning_request_from_row(row) if row is not None else None

    async def create_registration(
        self,
        *,
        directory_entry: DictionaryEntry | None,
        workspace: Workspace,
        request: ProvisioningRequest,
    ) -> WorkspaceRegistrationWriteResult:
        """Write registration records inside a savepoint so idempotency races leave no orphan."""

        try:
            async with self._session.begin_nested():
                if directory_entry is not None and not await self._insert_directory_entry(
                    directory_entry
                ):
                    raise _RegistrationWriteConflictError(
                        WorkspaceRegistrationWriteResult.DIRECTORY_ENTRY_EXISTS,
                    )
                if not await self._insert_workspace(workspace):
                    raise _RegistrationWriteConflictError(
                        WorkspaceRegistrationWriteResult.DIRECTORY_ENTRY_BOUND,
                    )
                if not await self._insert_request(request):
                    raise _RegistrationWriteConflictError(
                        WorkspaceRegistrationWriteResult.IDEMPOTENCY_KEY_EXISTS,
                    )
        except _RegistrationWriteConflictError as conflict:
            return conflict.result
        return WorkspaceRegistrationWriteResult.CREATED

    async def create_retry_request(self, request: ProvisioningRequest) -> bool:
        """Insert a durable retry request without changing migrator-owned readiness state."""

        return await self._insert_request(request)

    async def _insert_directory_entry(self, entry: DictionaryEntry) -> bool:
        statement = postgresql_insert(dictionary_entries_table).values(
            id=entry.id,
            dictionary_id=entry.dictionary_id,
            external_id=entry.external_id,
            label=entry.label,
            values=dict(entry.values),
            status=entry.status.value,
            sort_order=entry.sort_order,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing().returning(dictionary_entries_table.c.id),
        )
        return result.scalar_one_or_none() is not None

    async def _insert_workspace(self, workspace: Workspace) -> bool:
        statement = postgresql_insert(workspaces_table).values(
            id=workspace.id,
            directory_dictionary_id=workspace.directory_dictionary_id,
            directory_entry_id=workspace.directory_entry_id,
            schema_name=workspace.schema_name,
            schema_layout=workspace.schema_layout,
            storage_prefix=workspace.storage_prefix,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing().returning(workspaces_table.c.id),
        )
        return result.scalar_one_or_none() is not None

    async def _insert_request(self, request: ProvisioningRequest) -> bool:
        statement = postgresql_insert(workspace_provisioning_requests_table).values(
            id=request.id,
            workspace_id=request.workspace_id,
            idempotency_key=request.idempotency_key,
            payload_fingerprint=request.payload_fingerprint,
            target_revision=request.target_revision,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing().returning(
                workspace_provisioning_requests_table.c.id
            ),
        )
        return result.scalar_one_or_none() is not None


class _RegistrationWriteConflictError(Exception):
    """Private control flow used to roll back one savepoint."""

    def __init__(self, result: WorkspaceRegistrationWriteResult) -> None:
        self.result = result
