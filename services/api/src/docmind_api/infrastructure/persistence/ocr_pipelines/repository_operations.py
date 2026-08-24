"""Low-level OCR pipeline definition persistence operations."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineAuditAction,
    OcrPipelineDefinitionRecord,
    OcrPipelineDraftDefinition,
    OcrPipelineValidationResult,
    normalize_ocr_pipeline_name_key,
)
from docmind_api.infrastructure.persistence.ocr_pipelines.mappers import (
    DRAFT_VERSION_NUMBER,
    definition_to_json,
    json_object,
    record_from_rows,
    validation_to_json,
)
from docmind_api.infrastructure.persistence.ocr_pipelines.tables import (
    ocr_pipeline_definition_audit_events_table,
    ocr_pipeline_definition_names_table,
    ocr_pipeline_definition_versions_table,
    ocr_pipeline_definitions_table,
)


async def replace_versions(
    session: AsyncSession,
    record: OcrPipelineDefinitionRecord,
    *,
    audit_action: OcrPipelineAuditAction,
    actor_id: str | None,
) -> None:
    if record.draft is None:
        await session.execute(
            delete(ocr_pipeline_definition_versions_table).where(
                ocr_pipeline_definition_versions_table.c.definition_id == record.id,
                ocr_pipeline_definition_versions_table.c.version_number == DRAFT_VERSION_NUMBER,
            ),
        )
    else:
        await _upsert_draft_version(session, record, actor_id=actor_id)

    if record.published_definition is not None and record.published_version is not None:
        await _insert_published_version(
            session,
            record,
            audit_action=audit_action,
            actor_id=actor_id,
        )


async def replace_names(session: AsyncSession, record: OcrPipelineDefinitionRecord) -> bool:
    await session.execute(
        delete(ocr_pipeline_definition_names_table).where(
            ocr_pipeline_definition_names_table.c.definition_id == record.id,
        ),
    )
    for name in record_names(record):
        statement = postgresql_insert(ocr_pipeline_definition_names_table).values(
            normalized_name=name_key(name),
            definition_id=record.id,
            display_name=name,
        )
        result = await session.execute(
            statement.on_conflict_do_nothing().returning(
                ocr_pipeline_definition_names_table.c.normalized_name,
            ),
        )
        if result.scalar_one_or_none() is None:
            return False
    return True


async def has_name_conflict(
    session: AsyncSession,
    record: OcrPipelineDefinitionRecord,
    *,
    excluding_pipeline_id: UUID | None = None,
) -> bool:
    name_keys = tuple(name_key(name) for name in record_names(record))
    if not name_keys:
        return False
    statement = select(ocr_pipeline_definition_names_table.c.definition_id).where(
        ocr_pipeline_definition_names_table.c.normalized_name.in_(name_keys),
    )
    if excluding_pipeline_id is not None:
        statement = statement.where(
            ocr_pipeline_definition_names_table.c.definition_id != excluding_pipeline_id,
        )
    return (await session.scalar(statement)) is not None


async def record_from_id(
    session: AsyncSession,
    pipeline_id: UUID,
) -> OcrPipelineDefinitionRecord | None:
    result = await session.execute(
        select(ocr_pipeline_definitions_table).where(
            ocr_pipeline_definitions_table.c.id == pipeline_id,
        ),
    )
    row = result.mappings().one_or_none()
    if row is None:
        return None
    return await record_from_definition_row(session, row)


async def record_from_definition_row(
    session: AsyncSession,
    row: Mapping[Any, Any],
) -> OcrPipelineDefinitionRecord | None:
    result = await session.execute(
        select(ocr_pipeline_definition_versions_table)
        .where(ocr_pipeline_definition_versions_table.c.definition_id == row["id"])
        .order_by(ocr_pipeline_definition_versions_table.c.version_number.asc()),
    )
    version_rows = tuple(result.mappings())
    if not version_rows:
        return None
    return record_from_rows(row, version_rows)


async def delete_definition_rows(session: AsyncSession, pipeline_id: UUID) -> bool:
    result = await session.execute(
        delete(ocr_pipeline_definitions_table)
        .where(ocr_pipeline_definitions_table.c.id == pipeline_id)
        .returning(ocr_pipeline_definitions_table.c.id),
    )
    return result.scalar_one_or_none() is not None


async def add_audit_event(
    session: AsyncSession,
    *,
    pipeline_id: UUID,
    action: OcrPipelineAuditAction,
    actor_id: str | None,
    event_at: datetime,
    details: Mapping[str, Any],
) -> None:
    await session.execute(
        postgresql_insert(ocr_pipeline_definition_audit_events_table).values(
            id=uuid4(),
            pipeline_id=pipeline_id,
            action=action.value,
            actor_id=clean_actor_id(actor_id),
            event_at=event_at,
            details=json_object(details),
        ),
    )


def definition_insert_values(
    record: OcrPipelineDefinitionRecord,
    *,
    actor_id: str | None,
) -> dict[str, object]:
    values = _definition_base_values(record)
    cleaned_actor_id = clean_actor_id(actor_id)
    values.update(
        created_by_actor_id=cleaned_actor_id,
        updated_by_actor_id=cleaned_actor_id,
    )
    return values


def definition_update_values(
    record: OcrPipelineDefinitionRecord,
    *,
    audit_action: OcrPipelineAuditAction,
    actor_id: str | None,
) -> dict[str, object]:
    values = _definition_base_values(record)
    cleaned_actor_id = clean_actor_id(actor_id)
    values["updated_by_actor_id"] = cleaned_actor_id
    if audit_action == OcrPipelineAuditAction.PUBLISHED:
        values["published_by_actor_id"] = cleaned_actor_id
    if audit_action == OcrPipelineAuditAction.ARCHIVED:
        values["archived_by_actor_id"] = cleaned_actor_id
    return values


def record_audit_details(record: OcrPipelineDefinitionRecord) -> dict[str, object]:
    return {
        "lifecycle": record.lifecycle.value,
        "published_version": record.published_version,
        "is_default": record.is_default,
    }


def clean_actor_id(actor_id: str | None) -> str | None:
    if actor_id is None:
        return None
    normalized = actor_id.strip()
    return normalized or None


def coerce_uuid(value: UUID | str) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


def name_key(value: str) -> str:
    return normalize_ocr_pipeline_name_key(value)


async def _upsert_draft_version(
    session: AsyncSession,
    record: OcrPipelineDefinitionRecord,
    *,
    actor_id: str | None,
) -> None:
    assert record.draft is not None
    values = _version_values(
        record=record,
        definition=record.draft,
        version_number=DRAFT_VERSION_NUMBER,
        status="draft",
        validation=record.last_validation,
        compiled_snapshot=(
            record.last_validation.compiled_snapshot if record.last_validation is not None else None
        ),
        catalog_version=(
            record.last_validation.catalog_version if record.last_validation is not None else None
        ),
        catalog_hash=(
            record.last_validation.catalog_hash if record.last_validation is not None else None
        ),
        actor_id=actor_id,
    )
    statement = postgresql_insert(ocr_pipeline_definition_versions_table).values(**values)
    update_values = {
        key: values[key]
        for key in (
            "definition_json",
            "compiled_snapshot",
            "validation_result",
            "catalog_version",
            "catalog_hash",
            "updated_at",
            "updated_by_actor_id",
        )
    }
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[
                ocr_pipeline_definition_versions_table.c.definition_id,
                ocr_pipeline_definition_versions_table.c.version_number,
            ],
            set_=update_values,
        ),
    )


async def _insert_published_version(
    session: AsyncSession,
    record: OcrPipelineDefinitionRecord,
    *,
    audit_action: OcrPipelineAuditAction,
    actor_id: str | None,
) -> None:
    assert record.published_definition is not None
    assert record.published_version is not None
    values = _version_values(
        record=record,
        definition=record.published_definition,
        version_number=record.published_version,
        status="published",
        validation=record.last_validation,
        compiled_snapshot=record.compiled_snapshot,
        catalog_version=record.catalog_version,
        catalog_hash=record.catalog_hash,
        actor_id=actor_id if audit_action == OcrPipelineAuditAction.PUBLISHED else None,
    )
    statement = postgresql_insert(ocr_pipeline_definition_versions_table).values(**values)
    await session.execute(statement.on_conflict_do_nothing())


def _definition_base_values(record: OcrPipelineDefinitionRecord) -> dict[str, object]:
    definition = record.display_definition
    if definition is None:
        raise ValueError("OCR pipeline record must have a draft or published definition.")
    return {
        "id": record.id,
        "display_name": definition.name,
        "description": definition.description,
        "lifecycle": record.lifecycle.value,
        "is_default": record.is_default,
        "published_version": record.published_version,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "published_at": record.published_at,
        "archived_at": record.archived_at,
    }


def _version_values(
    *,
    record: OcrPipelineDefinitionRecord,
    definition: OcrPipelineDraftDefinition,
    version_number: int,
    status: str,
    validation: OcrPipelineValidationResult | None,
    compiled_snapshot: Mapping[str, Any] | None,
    catalog_version: str | None,
    catalog_hash: str | None,
    actor_id: str | None,
) -> dict[str, object]:
    event_at = record.published_at if status == "published" else record.updated_at
    created_at = event_at or record.updated_at
    return {
        "definition_id": record.id,
        "version_number": version_number,
        "status": status,
        "definition_json": definition_to_json(definition),
        "compiled_snapshot": json_object(compiled_snapshot)
        if compiled_snapshot is not None
        else None,
        "validation_result": validation_to_json(validation) if validation is not None else None,
        "catalog_version": catalog_version,
        "catalog_hash": catalog_hash,
        "created_at": created_at,
        "updated_at": created_at,
        "published_at": record.published_at if status == "published" else None,
        "created_by_actor_id": clean_actor_id(actor_id),
        "updated_by_actor_id": clean_actor_id(actor_id),
        "published_by_actor_id": clean_actor_id(actor_id) if status == "published" else None,
    }


def record_names(record: OcrPipelineDefinitionRecord) -> tuple[str, ...]:
    names_by_key: dict[str, str] = {}
    for definition in (record.draft, record.published_definition):
        if definition is None:
            continue
        names_by_key.setdefault(name_key(definition.name), definition.name)
    return tuple(names_by_key.values())
