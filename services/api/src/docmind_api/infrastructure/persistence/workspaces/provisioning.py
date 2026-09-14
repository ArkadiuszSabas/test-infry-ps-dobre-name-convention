"""Transactional, API-migrator execution of durable workspace provisioning requests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from docmind_api.infrastructure.persistence.workspaces.schema_baseline import (
    LOCAL_BASELINE_REVISION,
    WORKSPACE_PROVISIONING_TARGET_REVISION,
    apply_workspace_schema_baseline,
    verify_workspace_schema_baseline,
)
from docmind_api.infrastructure.persistence.workspaces.tables import (
    workspace_provisioning_requests_table,
    workspaces_table,
)


class WorkspaceProvisioningOutcome(StrEnum):
    """Safe terminal outcome reported by the operator command."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ALREADY_COMPLETED = "already_completed"


@dataclass(frozen=True, slots=True)
class WorkspaceProvisioningResult:
    """One request outcome without disclosing schema names or DDL details."""

    request_id: UUID
    outcome: WorkspaceProvisioningOutcome


class WorkspaceProvisioningConnectionLostError(RuntimeError):
    """The caller must stop because no final outcome can safely be persisted."""


class WorkspaceSchemaBaseline(Protocol):
    """Synchronous schema operations run on the executor's locked connection."""

    def apply(
        self,
        connection: Connection,
        *,
        schema_name: str,
        runtime_principal_name: str | None,
    ) -> None: ...

    def verify(self, connection: Connection, *, schema_name: str) -> None: ...


class SqlAlchemyWorkspaceSchemaBaseline:
    """Production adapter for the pinned local-schema baseline."""

    def apply(
        self,
        connection: Connection,
        *,
        schema_name: str,
        runtime_principal_name: str | None,
    ) -> None:
        apply_workspace_schema_baseline(
            connection,
            schema_name=schema_name,
            runtime_principal_name=runtime_principal_name,
        )

    def verify(self, connection: Connection, *, schema_name: str) -> None:
        verify_workspace_schema_baseline(connection, schema_name=schema_name)


class _WorkspaceProvisioningPreconditionError(RuntimeError):
    """A safe, non-DDL refusal that can be recorded as a failed request."""


async def provision_workspace_requests(
    *,
    engine: AsyncEngine,
    request_id: UUID | None,
    runtime_principal_name: str | None,
    schema_baseline: WorkspaceSchemaBaseline | None = None,
) -> tuple[WorkspaceProvisioningResult, ...]:
    """Provision one request or drain the pending queue in creation order.

    Every request uses its own transaction.  A single command consequently remains
    sequential without holding locks across independent workspaces.
    """

    baseline = schema_baseline or SqlAlchemyWorkspaceSchemaBaseline()
    if request_id is not None:
        return (
            await _provision_request(
                engine=engine,
                request_id=request_id,
                runtime_principal_name=runtime_principal_name,
                schema_baseline=baseline,
            ),
        )

    async with engine.connect() as connection:
        rows = await connection.execute(
            sa.select(workspace_provisioning_requests_table.c.id)
            .where(workspace_provisioning_requests_table.c.status == "pending")
            .order_by(
                workspace_provisioning_requests_table.c.created_at,
                workspace_provisioning_requests_table.c.id,
            )
        )
        pending_request_ids = tuple(UUID(str(value)) for value in rows.scalars())

    results: list[WorkspaceProvisioningResult] = []
    for pending_request_id in pending_request_ids:
        results.append(
            await _provision_request(
                engine=engine,
                request_id=pending_request_id,
                runtime_principal_name=runtime_principal_name,
                schema_baseline=baseline,
            )
        )
    return tuple(results)


async def _provision_request(
    *,
    engine: AsyncEngine,
    request_id: UUID,
    runtime_principal_name: str | None,
    schema_baseline: WorkspaceSchemaBaseline,
) -> WorkspaceProvisioningResult:
    async with engine.connect() as connection:
        async with connection.begin():
            workspace_id = await _request_workspace_id(connection=connection, request_id=request_id)
            workspace = await _locked_workspace(connection=connection, workspace_id=workspace_id)
            request = await _locked_request(connection=connection, request_id=request_id)
            if request is None or UUID(str(request["workspace_id"])) != workspace_id:
                raise _WorkspaceProvisioningPreconditionError(
                    "Workspace provisioning request ownership changed during execution."
                )
            if workspace is None:
                raise _WorkspaceProvisioningPreconditionError(
                    "Workspace provisioning request has no registered workspace."
                )

            if request["status"] == "succeeded":
                try:
                    await _verify_completed_request(
                        connection=connection,
                        workspace=workspace,
                        schema_baseline=schema_baseline,
                    )
                except Exception as error:
                    if connection.invalidated:
                        raise WorkspaceProvisioningConnectionLostError(
                            "Workspace provisioning connection was lost before final outcome."
                        ) from error
                    await _record_failure(
                        connection=connection,
                        request_id=request_id,
                        workspace_id=workspace_id,
                        mark_workspace_failed=True,
                    )
                    return WorkspaceProvisioningResult(
                        request_id=request_id,
                        outcome=WorkspaceProvisioningOutcome.FAILED,
                    )
                return WorkspaceProvisioningResult(
                    request_id=request_id,
                    outcome=WorkspaceProvisioningOutcome.ALREADY_COMPLETED,
                )
            if request["status"] == "failed":
                return WorkspaceProvisioningResult(
                    request_id=request_id,
                    outcome=WorkspaceProvisioningOutcome.FAILED,
                )

            try:
                _require_pending_request(workspace=workspace, request=request)
                await _start_retry_attempt_if_needed(
                    connection=connection,
                    workspace_id=workspace_id,
                    workspace=workspace,
                )
                async with connection.begin_nested():
                    await connection.run_sync(
                        lambda sync_connection: schema_baseline.apply(
                            sync_connection,
                            schema_name=str(workspace["schema_name"]),
                            runtime_principal_name=runtime_principal_name,
                        )
                    )
                    await connection.run_sync(
                        lambda sync_connection: schema_baseline.verify(
                            sync_connection,
                            schema_name=str(workspace["schema_name"]),
                        )
                    )
            except Exception as error:
                if connection.invalidated:
                    raise WorkspaceProvisioningConnectionLostError(
                        "Workspace provisioning connection was lost before final outcome."
                    ) from error
                await _record_failure(
                    connection=connection,
                    request_id=request_id,
                    workspace_id=workspace_id,
                    mark_workspace_failed=_is_provisionable_workspace(workspace),
                )
                return WorkspaceProvisioningResult(
                    request_id=request_id,
                    outcome=WorkspaceProvisioningOutcome.FAILED,
                )

            await _record_success(
                connection=connection, request_id=request_id, workspace_id=workspace_id
            )
            return WorkspaceProvisioningResult(
                request_id=request_id,
                outcome=WorkspaceProvisioningOutcome.SUCCEEDED,
            )


async def _request_workspace_id(*, connection: AsyncConnection, request_id: UUID) -> UUID:
    request_workspace_id = await connection.scalar(
        sa.select(workspace_provisioning_requests_table.c.workspace_id).where(
            workspace_provisioning_requests_table.c.id == request_id
        )
    )
    if request_workspace_id is None:
        raise _WorkspaceProvisioningPreconditionError(
            "Workspace provisioning request was not found."
        )
    return UUID(str(request_workspace_id))


async def _locked_workspace(
    *,
    connection: AsyncConnection,
    workspace_id: UUID,
) -> sa.RowMapping | None:
    result = await connection.execute(
        sa.select(workspaces_table).where(workspaces_table.c.id == workspace_id).with_for_update()
    )
    return result.mappings().one_or_none()


async def _locked_request(
    *,
    connection: AsyncConnection,
    request_id: UUID,
) -> sa.RowMapping | None:
    result = await connection.execute(
        sa.select(workspace_provisioning_requests_table)
        .where(workspace_provisioning_requests_table.c.id == request_id)
        .with_for_update()
    )
    return result.mappings().one_or_none()


def _require_pending_request(*, workspace: sa.RowMapping, request: sa.RowMapping) -> None:
    if request["status"] != "pending":
        raise _WorkspaceProvisioningPreconditionError(
            "Workspace provisioning request is not pending."
        )
    if request["target_revision"] != WORKSPACE_PROVISIONING_TARGET_REVISION:
        raise _WorkspaceProvisioningPreconditionError(
            "Workspace provisioning request targets an unsupported revision."
        )
    if workspace["lifecycle"] != "registered":
        raise _WorkspaceProvisioningPreconditionError(
            "Workspace is not registered for provisioning."
        )
    if not _is_provisionable_workspace(workspace):
        raise _WorkspaceProvisioningPreconditionError(
            "Workspace schema state is not eligible for provisioning."
        )


async def _start_retry_attempt_if_needed(
    *,
    connection: AsyncConnection,
    workspace_id: UUID,
    workspace: sa.RowMapping,
) -> None:
    if workspace["schema_state"] != "failed":
        return
    await connection.execute(
        sa.update(workspaces_table)
        .where(workspaces_table.c.id == workspace_id)
        .values(schema_state="pending", schema_revision=None, updated_at=sa.func.clock_timestamp())
    )


async def _verify_completed_request(
    *,
    connection: AsyncConnection,
    workspace: sa.RowMapping,
    schema_baseline: WorkspaceSchemaBaseline,
) -> None:
    if (
        workspace["lifecycle"] != "registered"
        or workspace["schema_state"] != "ready"
        or workspace["schema_revision"] != LOCAL_BASELINE_REVISION
    ):
        raise _WorkspaceProvisioningPreconditionError(
            "Completed workspace provisioning result does not match registry state."
        )
    await connection.run_sync(
        lambda sync_connection: schema_baseline.verify(
            sync_connection,
            schema_name=str(workspace["schema_name"]),
        )
    )


async def _record_success(
    *,
    connection: AsyncConnection,
    request_id: UUID,
    workspace_id: UUID,
) -> None:
    timestamp = sa.func.clock_timestamp()
    await connection.execute(
        sa.update(workspaces_table)
        .where(workspaces_table.c.id == workspace_id)
        .values(
            schema_state="ready",
            schema_revision=LOCAL_BASELINE_REVISION,
            updated_at=timestamp,
        )
    )
    await connection.execute(
        sa.update(workspace_provisioning_requests_table)
        .where(workspace_provisioning_requests_table.c.id == request_id)
        .values(
            status="succeeded",
            result_code="WORKSPACE_SCHEMA_READY",
            result_message="Workspace schema preparation completed.",
            updated_at=timestamp,
            completed_at=timestamp,
        )
    )


async def _record_failure(
    *,
    connection: AsyncConnection,
    request_id: UUID,
    workspace_id: UUID,
    mark_workspace_failed: bool,
) -> None:
    timestamp = sa.func.clock_timestamp()
    if mark_workspace_failed:
        await connection.execute(
            sa.update(workspaces_table)
            .where(workspaces_table.c.id == workspace_id)
            .values(schema_state="failed", schema_revision=None, updated_at=timestamp)
        )
    await connection.execute(
        sa.update(workspace_provisioning_requests_table)
        .where(workspace_provisioning_requests_table.c.id == request_id)
        .values(
            status="failed",
            result_code="WORKSPACE_SCHEMA_PREPARATION_FAILED",
            result_message="Workspace schema preparation requires operator retry or repair.",
            updated_at=timestamp,
            completed_at=timestamp,
        )
    )


def _is_provisionable_workspace(workspace: sa.RowMapping) -> bool:
    return (
        workspace["lifecycle"] == "registered"
        and workspace["schema_state"] in {"pending", "failed"}
        and workspace["schema_revision"] is None
    )
