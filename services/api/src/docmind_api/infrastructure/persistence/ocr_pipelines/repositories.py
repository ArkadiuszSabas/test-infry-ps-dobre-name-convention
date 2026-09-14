"""OCR pipeline definition repository implementations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from docmind_api.application.ocr_pipelines.commands import (
    ListOcrPipelinesQuery,
    OcrPipelineDefinitionList,
    OcrPipelineLifecycleFilter,
    OcrPipelineSortField,
)
from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineAuditAction,
    OcrPipelineDefinitionRecord,
)
from docmind_api.infrastructure.persistence.list_sorting import stable_order_by
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

    async def list(self, query: ListOcrPipelinesQuery) -> OcrPipelineDefinitionList:
        """Filter, sort, and page pipelines in persistence."""

        search_condition = None
        if query.search is not None:
            pattern = f"%{query.search}%"
            search_condition = or_(
                ocr_pipeline_definitions_table.c.display_name.ilike(pattern),
                ocr_pipeline_definitions_table.c.description.ilike(pattern),
            )
        conditions: list[ColumnElement[bool]] = []
        if search_condition is not None:
            conditions.append(search_condition)
        if query.lifecycle is not OcrPipelineLifecycleFilter.ALL:
            conditions.append(ocr_pipeline_definitions_table.c.lifecycle == query.lifecycle.value)

        statement = select(ocr_pipeline_definitions_table)
        count_statement = select(func.count(ocr_pipeline_definitions_table.c.id))
        if conditions:
            statement = statement.where(*conditions)
            count_statement = count_statement.where(*conditions)
        statement = (
            statement.order_by(
                *stable_order_by(
                    sort_by=query.sort_by,
                    direction=query.sort_direction,
                    allowlist={
                        OcrPipelineSortField.CREATED_AT: (
                            ocr_pipeline_definitions_table.c.created_at
                        ),
                        OcrPipelineSortField.LIFECYCLE: ocr_pipeline_definitions_table.c.lifecycle,
                        OcrPipelineSortField.NAME: ocr_pipeline_definitions_table.c.display_name,
                        OcrPipelineSortField.UPDATED_AT: (
                            ocr_pipeline_definitions_table.c.updated_at
                        ),
                    },
                    identity=ocr_pipeline_definitions_table.c.id,
                )
            )
            .limit(query.limit)
            .offset(query.offset)
        )
        result = await self._session.execute(statement)
        records: list[OcrPipelineDefinitionRecord] = []
        for row in result.mappings():
            record = await record_from_definition_row(self._session, row)
            if record is not None:
                records.append(record)
        lifecycle_count_statement = select(
            ocr_pipeline_definitions_table.c.lifecycle,
            func.count(ocr_pipeline_definitions_table.c.id),
        )
        if search_condition is not None:
            lifecycle_count_statement = lifecycle_count_statement.where(search_condition)
        lifecycle_count_statement = lifecycle_count_statement.group_by(
            ocr_pipeline_definitions_table.c.lifecycle
        )
        lifecycle_counts = {
            "draft": 0,
            "published": 0,
            "archived": 0,
        }
        for lifecycle, count in (await self._session.execute(lifecycle_count_statement)).all():
            lifecycle_counts[str(lifecycle)] = int(count)

        global_counts = (
            await self._session.execute(
                select(
                    func.count(ocr_pipeline_definitions_table.c.id),
                    func.count(ocr_pipeline_definitions_table.c.id).filter(
                        ocr_pipeline_definitions_table.c.lifecycle == "published"
                    ),
                    func.count(ocr_pipeline_definitions_table.c.id).filter(
                        ocr_pipeline_definitions_table.c.is_default.is_(True)
                    ),
                )
            )
        ).one()
        global_total, published_total, default_total = (int(value) for value in global_counts)
        routing_status = (
            "noPipelines"
            if global_total == 0
            else "noPublished"
            if published_total == 0
            else "noDefault"
            if default_total == 0
            else "ready"
        )
        return OcrPipelineDefinitionList(
            pipelines=tuple(records),
            total=int(await self._session.scalar(count_statement) or 0),
            limit=query.limit,
            offset=query.offset,
            lifecycle_counts=lifecycle_counts,
            routing_status=routing_status,
        )

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
