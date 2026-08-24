"""OCR pipeline definition repository implementations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineAuditAction,
    OcrPipelineDefinitionRecord,
)
from docmind_api.infrastructure.persistence.ocr_pipelines.repository_operations import (
    add_audit_event,
    clean_actor_id,
    coerce_uuid,
    definition_insert_values,
    definition_update_values,
    delete_definition_rows,
    has_name_conflict,
    name_key,
    record_audit_details,
    record_from_definition_row,
    record_from_id,
    replace_names,
    replace_versions,
)
from docmind_api.infrastructure.persistence.ocr_pipelines.tables import (
    ocr_pipeline_definition_names_table,
    ocr_pipeline_definitions_table,
)


class SqlAlchemyOcrPipelineDefinitionRepository:
    """PostgreSQL-backed OCR pipeline definition repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        record: OcrPipelineDefinitionRecord,
        *,
        actor_id: str | None = None,
    ) -> bool:
        """Store a new pipeline definition with an editable draft version."""

        if await has_name_conflict(self._session, record):
            return False
        statement = postgresql_insert(ocr_pipeline_definitions_table).values(
            **definition_insert_values(record, actor_id=actor_id),
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing().returning(
                ocr_pipeline_definitions_table.c.id,
            ),
        )
        if result.scalar_one_or_none() is None:
            return False

        await replace_versions(
            self._session,
            record,
            audit_action=OcrPipelineAuditAction.CREATED,
            actor_id=actor_id,
        )
        if not await replace_names(self._session, record):
            await delete_definition_rows(self._session, record.id)
            return False
        await add_audit_event(
            self._session,
            pipeline_id=record.id,
            action=OcrPipelineAuditAction.CREATED,
            actor_id=actor_id,
            event_at=record.created_at,
            details=record_audit_details(record),
        )
        return True

    async def save(
        self,
        record: OcrPipelineDefinitionRecord,
        *,
        audit_action: OcrPipelineAuditAction,
        expected_updated_at: datetime,
        actor_id: str | None = None,
    ) -> bool:
        """Persist an existing pipeline definition lifecycle or draft change."""

        if await has_name_conflict(self._session, record, excluding_pipeline_id=record.id):
            return False
        values = definition_update_values(
            record,
            audit_action=audit_action,
            actor_id=actor_id,
        )
        statement = (
            update(ocr_pipeline_definitions_table)
            .where(
                ocr_pipeline_definitions_table.c.id == record.id,
                ocr_pipeline_definitions_table.c.updated_at == expected_updated_at,
            )
            .values(**values)
            .returning(ocr_pipeline_definitions_table.c.id)
        )
        result = await self._session.execute(statement)
        if result.scalar_one_or_none() is None:
            return False

        await replace_versions(self._session, record, audit_action=audit_action, actor_id=actor_id)
        if not await replace_names(self._session, record):
            return False
        await add_audit_event(
            self._session,
            pipeline_id=record.id,
            action=audit_action,
            actor_id=actor_id,
            event_at=record.updated_at,
            details=record_audit_details(record),
        )
        return True

    async def get_by_id(self, pipeline_id: UUID | str) -> OcrPipelineDefinitionRecord | None:
        """Return one OCR pipeline definition by id."""

        normalized_id = coerce_uuid(pipeline_id)
        if normalized_id is None:
            return None
        return await record_from_id(self._session, normalized_id)

    async def get_by_name(self, name: str) -> OcrPipelineDefinitionRecord | None:
        """Return one OCR pipeline definition by reserved draft or published name."""

        statement = select(ocr_pipeline_definition_names_table.c.definition_id).where(
            ocr_pipeline_definition_names_table.c.normalized_name == name_key(name),
        )
        pipeline_id = await self._session.scalar(statement)
        if pipeline_id is None:
            return None
        return await record_from_id(self._session, pipeline_id)

    async def list(self) -> tuple[OcrPipelineDefinitionRecord, ...]:
        """Return pipelines ordered for administration display."""

        statement = select(ocr_pipeline_definitions_table).order_by(
            ocr_pipeline_definitions_table.c.display_name.asc(),
            ocr_pipeline_definitions_table.c.id.asc(),
        )
        result = await self._session.execute(statement)
        records: list[OcrPipelineDefinitionRecord] = []
        for row in result.mappings():
            record = await record_from_definition_row(self._session, row)
            if record is not None:
                records.append(record)
        return tuple(records)

    async def delete_by_id(
        self,
        pipeline_id: UUID | str,
        *,
        expected_updated_at: datetime,
        deleted_at: datetime,
        actor_id: str | None = None,
    ) -> bool:
        """Delete a never-published draft definition."""

        normalized_id = coerce_uuid(pipeline_id)
        if normalized_id is None:
            return False
        result = await self._session.execute(
            delete(ocr_pipeline_definitions_table)
            .where(
                ocr_pipeline_definitions_table.c.id == normalized_id,
                ocr_pipeline_definitions_table.c.lifecycle == "draft",
                ocr_pipeline_definitions_table.c.published_version.is_(None),
                ocr_pipeline_definitions_table.c.updated_at == expected_updated_at,
            )
            .returning(ocr_pipeline_definitions_table.c.id),
        )
        if result.scalar_one_or_none() is None:
            return False
        await add_audit_event(
            self._session,
            pipeline_id=normalized_id,
            action=OcrPipelineAuditAction.DELETED,
            actor_id=actor_id,
            event_at=deleted_at,
            details={"deleted": True},
        )
        return True

    async def set_default(
        self,
        pipeline_id: UUID,
        *,
        changed_at: datetime,
        actor_id: str | None = None,
    ) -> OcrPipelineDefinitionRecord | None:
        """Mark one published pipeline as the default and clear other defaults."""

        await self._session.execute(select(ocr_pipeline_definitions_table.c.id).with_for_update())
        target = await record_from_id(self._session, pipeline_id)
        if (
            target is None
            or not target.has_published_version
            or target.lifecycle.value != "published"
        ):
            return None
        previous_default_ids = tuple(
            row.id
            for row in await self._session.execute(
                select(ocr_pipeline_definitions_table.c.id).where(
                    ocr_pipeline_definitions_table.c.is_default.is_(True),
                    ocr_pipeline_definitions_table.c.id != pipeline_id,
                ),
            )
        )
        await self._session.execute(
            update(ocr_pipeline_definitions_table)
            .where(
                ocr_pipeline_definitions_table.c.is_default.is_(True),
                ocr_pipeline_definitions_table.c.id != pipeline_id,
            )
            .values(
                is_default=False,
                updated_at=changed_at,
                updated_by_actor_id=clean_actor_id(actor_id),
                default_set_by_actor_id=clean_actor_id(actor_id),
            ),
        )
        statement = (
            update(ocr_pipeline_definitions_table)
            .where(ocr_pipeline_definitions_table.c.id == pipeline_id)
            .values(
                is_default=True,
                updated_at=changed_at,
                updated_by_actor_id=clean_actor_id(actor_id),
                default_set_by_actor_id=clean_actor_id(actor_id),
            )
            .returning(ocr_pipeline_definitions_table.c.id)
        )
        result = await self._session.execute(statement)
        if result.scalar_one_or_none() is None:
            return None
        updated = await record_from_id(self._session, pipeline_id)
        if updated is None:
            return None
        for previous_default_id in previous_default_ids:
            await add_audit_event(
                self._session,
                pipeline_id=previous_default_id,
                action=OcrPipelineAuditAction.DEFAULT_CHANGED,
                actor_id=actor_id,
                event_at=changed_at,
                details={"is_default": False},
            )
        await add_audit_event(
            self._session,
            pipeline_id=pipeline_id,
            action=OcrPipelineAuditAction.DEFAULT_CHANGED,
            actor_id=actor_id,
            event_at=changed_at,
            details=record_audit_details(updated),
        )
        return updated
