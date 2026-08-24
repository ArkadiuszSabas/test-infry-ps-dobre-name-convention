"""PostgreSQL repository for connector approved-document archive state."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from hashlib import blake2b
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docmind_api.application.connectors.document_archives import (
    ConnectorDocumentArchiveRepository,
)
from docmind_api.infrastructure.persistence.connectors.document_archive_tables import (
    connector_document_archives_table,
)
from docmind_core.connectors import (
    ConnectorDocumentArchive,
    ConnectorDocumentArchiveFailureStage,
    ConnectorDocumentArchivePlan,
    ConnectorDocumentArchiveStatus,
)


class SqlAlchemyConnectorDocumentArchiveRepository(ConnectorDocumentArchiveRepository):
    """Keep retry-stable plans and safe terminal results under row locks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def reserve(
        self,
        plan: ConnectorDocumentArchivePlan,
    ) -> ConnectorDocumentArchive:
        now = datetime.now(tz=UTC)
        await self._session.execute(
            postgresql_insert(connector_document_archives_table)
            .values(**_pending_values(plan, created_at=now, updated_at=now))
            .on_conflict_do_nothing(
                index_elements=[connector_document_archives_table.c.document_id],
            )
        )
        current = await self._get_for_update(plan.document_id)
        if current is None:
            raise RuntimeError("Connector document archive reservation did not persist.")
        if (
            current.plan.review_version == plan.review_version
            and current.plan.handler_id == plan.handler_id
        ):
            if current.status is ConnectorDocumentArchiveStatus.FAILED:
                if current.failure_stage is ConnectorDocumentArchiveFailureStage.PREFLIGHT:
                    await self._session.execute(
                        update(connector_document_archives_table)
                        .where(connector_document_archives_table.c.document_id == plan.document_id)
                        .values(
                            **_pending_values(
                                plan,
                                created_at=current.created_at,
                                updated_at=now,
                            )
                        )
                    )
                    return await self._require(plan.document_id)
                await self._session.execute(
                    update(connector_document_archives_table)
                    .where(connector_document_archives_table.c.document_id == plan.document_id)
                    .values(
                        status=ConnectorDocumentArchiveStatus.PENDING.value,
                        drive_item_id=None,
                        web_url=None,
                        error_code=None,
                        failure_stage=None,
                        updated_at=now,
                    )
                )
                return await self._require(plan.document_id)
            return current
        await self._session.execute(
            update(connector_document_archives_table)
            .where(connector_document_archives_table.c.document_id == plan.document_id)
            .values(**_pending_values(plan, created_at=current.created_at, updated_at=now))
        )
        return await self._require(plan.document_id)

    async def succeed(
        self,
        plan: ConnectorDocumentArchivePlan,
        *,
        drive_item_id: str,
        web_url: str,
    ) -> ConnectorDocumentArchive:
        await self._set_terminal(
            plan,
            status=ConnectorDocumentArchiveStatus.SUCCEEDED,
            drive_item_id=drive_item_id,
            web_url=web_url,
            error_code=None,
            failure_stage=None,
            preserve_success=False,
        )
        return await self._require(plan.document_id)

    async def fail(
        self,
        plan: ConnectorDocumentArchivePlan,
        *,
        error_code: str,
        failure_stage: ConnectorDocumentArchiveFailureStage,
    ) -> ConnectorDocumentArchive:
        await self._set_terminal(
            plan,
            status=ConnectorDocumentArchiveStatus.FAILED,
            drive_item_id=None,
            web_url=None,
            error_code=error_code,
            failure_stage=failure_stage,
            preserve_success=True,
        )
        return await self._require(plan.document_id)

    async def get(self, document_id: UUID) -> ConnectorDocumentArchive | None:
        """Return current archive state without locking it."""

        result = await self._session.execute(
            select(connector_document_archives_table).where(
                connector_document_archives_table.c.document_id == document_id
            )
        )
        row = result.mappings().one_or_none()
        return _from_row(row) if row is not None else None

    async def get_succeeded_web_urls(
        self,
        document_ids: tuple[UUID, ...],
    ) -> dict[UUID, str]:
        """Return durable archive permalinks for the requested documents."""

        if not document_ids:
            return {}

        result = await self._session.execute(
            select(
                connector_document_archives_table.c.document_id,
                connector_document_archives_table.c.web_url,
            ).where(
                connector_document_archives_table.c.document_id.in_(document_ids),
                connector_document_archives_table.c.status
                == ConnectorDocumentArchiveStatus.SUCCEEDED.value,
            )
        )
        return {row.document_id: str(row.web_url) for row in result if row.web_url is not None}

    async def is_execution_active(self, document_id: UUID) -> bool:
        """Report whether an approved-document handler currently owns the IO lock."""

        lock_key = connector_document_archive_lock_key(document_id)
        acquired = bool(await self._session.scalar(select(func.pg_try_advisory_lock(lock_key))))
        if not acquired:
            return True
        unlocked = bool(await self._session.scalar(select(func.pg_advisory_unlock(lock_key))))
        if not unlocked:
            raise RuntimeError("Connector archive advisory lock was not released.")
        return False

    async def cancel(
        self,
        document_id: UUID,
        *,
        error_code: str,
    ) -> ConnectorDocumentArchive | None:
        """Cancel pending work only when no approved-document handler owns its IO lock."""

        current = await self.get(document_id)
        if current is None:
            return None
        if current.status is not ConnectorDocumentArchiveStatus.PENDING:
            return current
        lock_key = connector_document_archive_lock_key(document_id)
        acquired = bool(
            await self._session.scalar(select(func.pg_try_advisory_xact_lock(lock_key)))
        )
        if not acquired:
            return current
        current = await self._get_for_update(document_id)
        if current is None:
            return None
        if current.status is not ConnectorDocumentArchiveStatus.PENDING:
            return current
        await self._session.execute(
            update(connector_document_archives_table)
            .where(connector_document_archives_table.c.document_id == document_id)
            .values(
                status=ConnectorDocumentArchiveStatus.CANCELLED.value,
                drive_item_id=None,
                web_url=None,
                error_code=error_code,
                failure_stage=None,
                updated_at=datetime.now(tz=UTC),
            )
        )
        return await self._require(document_id)

    async def _set_terminal(
        self,
        plan: ConnectorDocumentArchivePlan,
        *,
        status: ConnectorDocumentArchiveStatus,
        drive_item_id: str | None,
        web_url: str | None,
        error_code: str | None,
        failure_stage: ConnectorDocumentArchiveFailureStage | None,
        preserve_success: bool,
    ) -> None:
        statement = update(connector_document_archives_table).where(
            connector_document_archives_table.c.document_id == plan.document_id,
            connector_document_archives_table.c.handler_id == plan.handler_id,
            connector_document_archives_table.c.review_version == plan.review_version,
            connector_document_archives_table.c.status
            != ConnectorDocumentArchiveStatus.CANCELLED.value,
        )
        if preserve_success:
            statement = statement.where(
                connector_document_archives_table.c.status
                != ConnectorDocumentArchiveStatus.SUCCEEDED.value
            )
        result = await self._session.execute(
            statement.values(
                status=status.value,
                drive_item_id=drive_item_id,
                web_url=web_url,
                error_code=error_code,
                failure_stage=failure_stage.value if failure_stage is not None else None,
                updated_at=datetime.now(tz=UTC),
            ).returning(connector_document_archives_table.c.document_id)
        )
        if result.scalar_one_or_none() is not None:
            return
        current = await self._require(plan.document_id)
        if (
            preserve_success
            and current.plan.handler_id == plan.handler_id
            and current.plan.review_version == plan.review_version
            and current.status is ConnectorDocumentArchiveStatus.SUCCEEDED
        ):
            return
        if current.status is ConnectorDocumentArchiveStatus.CANCELLED:
            return
        raise RuntimeError("Connector document archive plan changed before completion.")

    async def _get_for_update(self, document_id: UUID) -> ConnectorDocumentArchive | None:
        result = await self._session.execute(
            select(connector_document_archives_table)
            .where(connector_document_archives_table.c.document_id == document_id)
            .with_for_update()
        )
        row = result.mappings().one_or_none()
        return _from_row(row) if row is not None else None

    async def _require(self, document_id: UUID) -> ConnectorDocumentArchive:
        result = await self._session.execute(
            select(connector_document_archives_table).where(
                connector_document_archives_table.c.document_id == document_id
            )
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise RuntimeError("Connector document archive state was not found.")
        return _from_row(row)


def _pending_values(
    plan: ConnectorDocumentArchivePlan,
    *,
    created_at: datetime,
    updated_at: datetime,
) -> dict[str, object]:
    return {
        "document_id": plan.document_id,
        "connector_instance_id": plan.connector_instance_id,
        "handler_id": plan.handler_id,
        "review_version": plan.review_version,
        "status": ConnectorDocumentArchiveStatus.PENDING.value,
        "approved_at": plan.approved_at,
        "folder_path": plan.folder_path,
        "file_name": plan.file_name,
        "drive_item_id": None,
        "web_url": None,
        "error_code": None,
        "failure_stage": None,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def connector_document_archive_lock_key(document_id: UUID) -> int:
    """Return a namespace-scoped signed 64-bit PostgreSQL advisory-lock key."""

    digest = blake2b(
        document_id.bytes,
        digest_size=8,
        person=b"dm-archive-lock",
    ).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


@asynccontextmanager
async def connector_document_archive_execution_lock(
    session_factory: async_sessionmaker[AsyncSession],
    document_id: UUID,
) -> AsyncGenerator[None]:
    """Hold a crash-safe session lock across connector-owned archive IO."""

    lock_key = connector_document_archive_lock_key(document_id)
    async with session_factory() as session:
        await session.scalar(select(func.pg_advisory_lock(lock_key)))
        try:
            yield
        finally:
            unlocked = bool(await session.scalar(select(func.pg_advisory_unlock(lock_key))))
            if not unlocked:
                raise RuntimeError("Connector archive advisory lock was not released.")


def _from_row(row: RowMapping) -> ConnectorDocumentArchive:
    plan = ConnectorDocumentArchivePlan(
        document_id=row["document_id"],
        connector_instance_id=str(row["connector_instance_id"]),
        handler_id=str(row["handler_id"]),
        review_version=int(row["review_version"]),
        approved_at=row["approved_at"],
        folder_path=str(row["folder_path"]),
        file_name=str(row["file_name"]),
    )
    return ConnectorDocumentArchive(
        plan=plan,
        status=ConnectorDocumentArchiveStatus(str(row["status"])),
        drive_item_id=row["drive_item_id"],
        web_url=row["web_url"],
        error_code=row["error_code"],
        failure_stage=(
            ConnectorDocumentArchiveFailureStage(str(row["failure_stage"]))
            if row["failure_stage"] is not None
            else None
        ),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
