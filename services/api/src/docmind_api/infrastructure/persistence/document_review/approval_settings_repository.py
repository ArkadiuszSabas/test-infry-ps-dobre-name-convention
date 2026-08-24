"""PostgreSQL persistence for global document approval settings."""

from datetime import datetime

from sqlalchemy import exists, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.domain.documents.approval import DocumentApprovalWorkflowStatus
from docmind_api.domain.documents.approval_settings import DocumentApprovalSettings
from docmind_api.infrastructure.persistence.document_review.tables import (
    document_approval_decisions_table,
    document_approval_settings_table,
    document_approval_workflows_table,
)
from docmind_api.infrastructure.persistence.documents.tables import documents_table

SETTINGS_KEY = "default"


class SqlAlchemyDocumentApprovalSettingsRepository:
    """Store the single API-owned document approval configuration."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> DocumentApprovalSettings | None:
        """Return the stored override when one exists."""

        row = (
            (
                await self._session.execute(
                    select(document_approval_settings_table).where(
                        document_approval_settings_table.c.settings_key == SETTINGS_KEY,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else _settings_from_row(row)

    async def save(
        self,
        settings: DocumentApprovalSettings,
        *,
        expected_updated_at: datetime | None,
    ) -> DocumentApprovalSettings | None:
        """Replace settings only when the caller owns the loaded version."""

        if settings.updated_at is None or settings.updated_by_actor_id is None:
            raise ValueError("Persisted document approval settings require audit fields.")
        values = {
            "schema_version": settings.schema_version,
            "required_approvals": settings.required_approvals,
            "updated_at": settings.updated_at,
            "updated_by_actor_id": settings.updated_by_actor_id,
        }
        if expected_updated_at is None:
            statement = (
                postgresql_insert(document_approval_settings_table)
                .values(settings_key=SETTINGS_KEY, **values)
                .on_conflict_do_nothing(
                    index_elements=[document_approval_settings_table.c.settings_key]
                )
                .returning(document_approval_settings_table)
            )
        else:
            statement = (
                update(document_approval_settings_table)
                .where(
                    document_approval_settings_table.c.settings_key == SETTINGS_KEY,
                    document_approval_settings_table.c.updated_at == expected_updated_at,
                )
                .values(**values)
                .returning(document_approval_settings_table)
            )
        row = (await self._session.execute(statement)).mappings().one_or_none()
        if row is None:
            return None
        saved = _settings_from_row(row)
        await self._apply_to_unstarted_workflows(saved)
        return saved

    async def _apply_to_unstarted_workflows(
        self,
        settings: DocumentApprovalSettings,
    ) -> None:
        """Update workflows that have never recorded an approval decision."""

        no_decisions_for_document = ~exists().where(
            document_approval_decisions_table.c.document_id == documents_table.c.id
        )
        # Approval decisions lock the same document row before writing history.
        # Locking here first serializes propagation with a concurrent first decision;
        # the following UPDATE then rechecks history after any lock wait.
        locked_documents = await self._session.execute(
            select(documents_table.c.id)
            .join(
                document_approval_workflows_table,
                document_approval_workflows_table.c.document_id == documents_table.c.id,
            )
            .where(
                document_approval_workflows_table.c.status
                == DocumentApprovalWorkflowStatus.WAITING_FOR_REVIEW.value,
                no_decisions_for_document,
            )
            .order_by(documents_table.c.id)
            .with_for_update(of=documents_table)
        )
        locked_documents.scalars().all()

        no_workflow_decisions = ~exists().where(
            document_approval_decisions_table.c.document_id
            == document_approval_workflows_table.c.document_id
        )
        await self._session.execute(
            update(document_approval_workflows_table)
            .where(
                document_approval_workflows_table.c.status
                == DocumentApprovalWorkflowStatus.WAITING_FOR_REVIEW.value,
                no_workflow_decisions,
                document_approval_workflows_table.c.required_approvals
                != settings.required_approvals,
            )
            .values(
                required_approvals=settings.required_approvals,
                updated_at=settings.updated_at,
            )
        )


def _settings_from_row(row: RowMapping) -> DocumentApprovalSettings:
    return DocumentApprovalSettings(
        schema_version=int(row["schema_version"]),
        required_approvals=int(row["required_approvals"]),
        updated_at=row["updated_at"],
        updated_by_actor_id=str(row["updated_by_actor_id"]),
    )
