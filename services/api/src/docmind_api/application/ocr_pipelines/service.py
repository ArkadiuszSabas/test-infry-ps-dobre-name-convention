"""OCR pipeline admin application use cases."""

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from docmind_api.application.ocr_pipelines.commands import (
    ArchiveOcrPipelineCommand,
    CreateOcrPipelineCommand,
    DeleteOcrPipelineCommand,
    DeleteOcrPipelineResult,
    GetOcrPipelineQuery,
    ListOcrPipelinesQuery,
    MakeDefaultOcrPipelineCommand,
    OcrPipelineDefinitionList,
    PreserveOcrPipelineDraftField,
    PublishOcrPipelineCommand,
    UpdateOcrPipelineDraftCommand,
    ValidateOcrPipelineCommand,
)
from docmind_api.application.ocr_pipelines.draft_validation import draft_write_diagnostics
from docmind_api.application.ocr_pipelines.errors import (
    OcrPipelineAlreadyExistsError,
    OcrPipelineLifecycleError,
    OcrPipelineNotFoundError,
    OcrPipelineValidationError,
    OcrPipelineValidationFailedError,
)
from docmind_api.application.ocr_pipelines.ports import (
    AttributeDefinitionReferenceCatalog,
    Clock,
    DocumentTypeReferenceCatalog,
    OcrPipelineBlockCatalogClient,
    OcrPipelineDefinitionRepository,
    OcrPipelineIdFactory,
)
from docmind_api.application.ocr_pipelines.reference_validation import reference_diagnostics
from docmind_api.application.ocr_pipelines.validation import product_diagnostics
from docmind_api.domain.ocr_pipelines.models import (
    OcrPipelineAuditAction,
    OcrPipelineBlockCatalog,
    OcrPipelineDefinitionRecord,
    OcrPipelineDraftDefinition,
    OcrPipelineKind,
    OcrPipelineLifecycle,
    OcrPipelineStepDefinition,
    OcrPipelineValidationResult,
)


class OcrPipelineAdminService:
    """Application service for OCR pipeline admin workflows."""

    def __init__(
        self,
        *,
        repository: OcrPipelineDefinitionRepository,
        block_catalog_client: OcrPipelineBlockCatalogClient,
        clock: Clock,
        id_factory: OcrPipelineIdFactory,
        document_type_reference_catalog: DocumentTypeReferenceCatalog | None = None,
        attribute_reference_catalog: AttributeDefinitionReferenceCatalog | None = None,
    ) -> None:
        self._repository = repository
        self._block_catalog_client = block_catalog_client
        self._clock = clock
        self._id_factory = id_factory
        self._document_type_reference_catalog = document_type_reference_catalog
        self._attribute_reference_catalog = attribute_reference_catalog

    async def get_block_catalog(self) -> OcrPipelineBlockCatalog:
        """Return the API-safe OCR pipeline block catalog."""

        return await self._block_catalog_client.get_catalog()

    async def list_pipelines(self, query: ListOcrPipelinesQuery) -> OcrPipelineDefinitionList:
        """Return configured OCR pipeline definitions."""

        return OcrPipelineDefinitionList(pipelines=await self._repository.list())

    async def create_pipeline(
        self,
        command: CreateOcrPipelineCommand,
    ) -> OcrPipelineDefinitionRecord:
        """Create a new editable OCR pipeline draft."""

        definition = _draft_definition_from_input(
            name=command.name,
            description=command.description,
            steps=command.steps,
        )
        await self._raise_if_draft_write_invalid(definition)
        await self._raise_if_name_conflicts(definition.name)
        timestamp = self._clock.now()
        record = OcrPipelineDefinitionRecord(
            id=self._id_factory.new_id(),
            lifecycle=OcrPipelineLifecycle.DRAFT,
            draft=definition,
            created_at=timestamp,
            updated_at=timestamp,
        )
        created = await self._repository.add(record, actor_id=command.actor_id)
        if not created:
            raise OcrPipelineAlreadyExistsError(name=definition.name)
        return record

    async def get_pipeline(self, query: GetOcrPipelineQuery) -> OcrPipelineDefinitionRecord:
        """Return one OCR pipeline definition."""

        return await self._get_record(query.pipeline_id)

    async def update_draft(
        self,
        command: UpdateOcrPipelineDraftCommand,
    ) -> OcrPipelineDefinitionRecord:
        """Edit draft metadata and ordered steps."""

        record = await self._get_record(command.pipeline_id)
        if record.lifecycle == OcrPipelineLifecycle.ARCHIVED:
            raise _lifecycle_error(record.id, "Archived OCR pipelines cannot be edited.")

        base_definition = record.draft or record.published_definition
        if base_definition is None:
            raise _lifecycle_error(record.id, "OCR pipeline has no draft to edit.")

        definition = _draft_definition_from_input(
            name=_resolve_update(command.name, base_definition.name),
            description=_resolve_update(command.description, base_definition.description),
            steps=_resolve_update(command.steps, base_definition.steps),
        )
        await self._raise_if_draft_write_invalid(definition)
        await self._raise_if_name_conflicts(definition.name, excluding_pipeline_id=record.id)
        updated = replace(
            record,
            lifecycle=(
                OcrPipelineLifecycle.PUBLISHED
                if record.has_published_version
                else OcrPipelineLifecycle.DRAFT
            ),
            draft=definition,
            updated_at=self._clock.now(),
            last_validation=None,
        )
        return await self._save_existing(
            updated,
            audit_action=OcrPipelineAuditAction.DRAFT_UPDATED,
            expected_updated_at=record.updated_at,
            actor_id=command.actor_id,
        )

    async def validate_pipeline(
        self,
        command: ValidateOcrPipelineCommand,
    ) -> OcrPipelineValidationResult:
        """Validate one draft without publishing it."""

        record = await self._get_record(command.pipeline_id)
        if record.lifecycle == OcrPipelineLifecycle.ARCHIVED:
            raise _lifecycle_error(record.id, "Archived OCR pipelines cannot be validated.")
        if record.draft is None:
            raise _lifecycle_error(
                record.id,
                "OCR pipeline does not have an editable draft to validate.",
            )

        validation = await self._validate_definition(record.id, record.draft)
        await self._save_existing(
            replace(record, last_validation=validation, updated_at=self._clock.now()),
            audit_action=OcrPipelineAuditAction.VALIDATED,
            expected_updated_at=record.updated_at,
            actor_id=command.actor_id,
        )
        return validation

    async def publish_pipeline(
        self,
        command: PublishOcrPipelineCommand,
    ) -> OcrPipelineDefinitionRecord:
        """Publish an immutable version when validation succeeds."""

        record = await self._get_record(command.pipeline_id)
        if record.lifecycle == OcrPipelineLifecycle.ARCHIVED:
            raise _lifecycle_error(record.id, "Archived OCR pipelines cannot be published.")
        if record.draft is None:
            raise _lifecycle_error(record.id, "OCR pipeline does not have a draft to publish.")

        validation = await self._validate_definition(record.id, record.draft)
        if not validation.valid:
            raise OcrPipelineValidationFailedError(
                pipeline_id=record.id,
                diagnostics=validation.diagnostics,
            )

        timestamp = self._clock.now()
        updated = replace(
            record,
            lifecycle=OcrPipelineLifecycle.PUBLISHED,
            draft=None,
            published_definition=record.draft,
            published_version=(record.published_version or 0) + 1,
            published_at=timestamp,
            archived_at=None,
            updated_at=timestamp,
            last_validation=validation,
            compiled_snapshot=validation.compiled_snapshot,
            catalog_version=validation.catalog_version,
            catalog_hash=validation.catalog_hash,
        )
        return await self._save_existing(
            updated,
            audit_action=OcrPipelineAuditAction.PUBLISHED,
            expected_updated_at=record.updated_at,
            actor_id=command.actor_id,
        )

    async def archive_pipeline(
        self,
        command: ArchiveOcrPipelineCommand,
    ) -> OcrPipelineDefinitionRecord:
        """Archive a previously published OCR pipeline."""

        record = await self._get_record(command.pipeline_id)
        if record.lifecycle == OcrPipelineLifecycle.ARCHIVED:
            raise _lifecycle_error(record.id, "OCR pipeline is already archived.")
        if not record.has_published_version:
            raise _lifecycle_error(
                record.id,
                "Never-published OCR pipeline drafts should be deleted, not archived.",
            )

        timestamp = self._clock.now()
        updated = replace(
            record,
            lifecycle=OcrPipelineLifecycle.ARCHIVED,
            draft=None,
            is_default=False,
            archived_at=timestamp,
            updated_at=timestamp,
        )
        return await self._save_existing(
            updated,
            audit_action=OcrPipelineAuditAction.ARCHIVED,
            expected_updated_at=record.updated_at,
            actor_id=command.actor_id,
        )

    async def delete_pipeline(self, command: DeleteOcrPipelineCommand) -> DeleteOcrPipelineResult:
        """Delete only a never-published draft."""

        record = await self._get_record(command.pipeline_id)
        if record.has_published_version:
            raise _lifecycle_error(
                record.id,
                "Published OCR pipelines must be archived instead of deleted.",
            )
        deleted_at = self._clock.now()
        deleted = await self._repository.delete_by_id(
            record.id,
            expected_updated_at=record.updated_at,
            deleted_at=deleted_at,
            actor_id=command.actor_id,
        )
        if not deleted:
            current = await self._repository.get_by_id(record.id)
            if current is None:
                raise OcrPipelineNotFoundError(pipeline_id=record.id)
            raise _lifecycle_error(
                record.id,
                "OCR pipeline changed concurrently; reload before retrying.",
            )
        return DeleteOcrPipelineResult(pipeline_id=record.id, deleted=True)

    async def make_default_pipeline(
        self,
        command: MakeDefaultOcrPipelineCommand,
    ) -> OcrPipelineDefinitionRecord:
        """Select one published OCR pipeline as the default."""

        record = await self._get_record(command.pipeline_id)
        if record.lifecycle == OcrPipelineLifecycle.ARCHIVED:
            raise _lifecycle_error(
                record.id, "Archived OCR pipelines cannot be selected as default."
            )
        if not record.has_published_version:
            raise _lifecycle_error(
                record.id, "Only published OCR pipelines can be selected as default."
            )

        updated = await self._repository.set_default(
            record.id,
            changed_at=self._clock.now(),
            actor_id=command.actor_id,
        )
        if updated is None:
            await self._raise_default_selection_conflict(record.id)
            raise AssertionError("unreachable default-selection conflict path")
        return updated

    async def _raise_if_draft_write_invalid(
        self,
        definition: OcrPipelineDraftDefinition,
    ) -> None:
        catalog = await self._block_catalog_client.get_catalog()
        diagnostics = draft_write_diagnostics(definition=definition, catalog=catalog)
        if not diagnostics:
            return
        raise OcrPipelineValidationError(
            message="OCR pipeline draft contains unsupported or unsafe step config.",
            details={
                "diagnostics": tuple(diagnostic.as_details() for diagnostic in diagnostics),
            },
        )

    async def _validate_definition(
        self,
        pipeline_id: UUID,
        definition: OcrPipelineDraftDefinition,
    ) -> OcrPipelineValidationResult:
        catalog = await self._block_catalog_client.get_catalog()
        diagnostics = list(product_diagnostics(definition=definition, catalog=catalog))
        diagnostics.extend(
            await reference_diagnostics(
                definition=definition,
                document_type_reference_catalog=self._document_type_reference_catalog,
                attribute_reference_catalog=self._attribute_reference_catalog,
            ),
        )

        if any(diagnostic.is_error for diagnostic in diagnostics):
            return OcrPipelineValidationResult(
                diagnostics=tuple(diagnostics),
                catalog_version=catalog.catalog_version,
                catalog_hash=catalog.catalog_hash,
            )

        technical_validation = await self._block_catalog_client.compile_definition(
            pipeline_id, definition
        )
        diagnostics.extend(technical_validation.diagnostics)
        return OcrPipelineValidationResult(
            diagnostics=tuple(diagnostics),
            compiled_snapshot=technical_validation.compiled_snapshot,
            catalog_version=technical_validation.catalog_version or catalog.catalog_version,
            catalog_hash=technical_validation.catalog_hash or catalog.catalog_hash,
        )

    async def _get_record(self, pipeline_id: UUID | str) -> OcrPipelineDefinitionRecord:
        record = await self._repository.get_by_id(pipeline_id)
        if record is None:
            raise OcrPipelineNotFoundError(pipeline_id=pipeline_id)
        return record

    async def _save_existing(
        self,
        record: OcrPipelineDefinitionRecord,
        *,
        audit_action: OcrPipelineAuditAction,
        expected_updated_at: datetime,
        actor_id: str | None,
    ) -> OcrPipelineDefinitionRecord:
        saved = await self._repository.save(
            record,
            audit_action=audit_action,
            expected_updated_at=expected_updated_at,
            actor_id=actor_id,
        )
        if saved:
            return record
        current = await self._repository.get_by_id(record.id)
        if current is None:
            raise OcrPipelineNotFoundError(pipeline_id=record.id)
        await self._raise_if_record_name_conflicts(record)
        if current.updated_at != expected_updated_at:
            raise _lifecycle_error(
                record.id,
                "OCR pipeline changed concurrently; reload before retrying.",
            )
        raise OcrPipelineAlreadyExistsError(name=_record_display_name(record))

    async def _raise_default_selection_conflict(self, pipeline_id: UUID) -> None:
        current = await self._repository.get_by_id(pipeline_id)
        if current is None:
            raise OcrPipelineNotFoundError(pipeline_id=pipeline_id)
        if current.lifecycle == OcrPipelineLifecycle.ARCHIVED:
            raise _lifecycle_error(
                current.id, "Archived OCR pipelines cannot be selected as default."
            )
        if not current.has_published_version:
            raise _lifecycle_error(
                current.id, "Only published OCR pipelines can be selected as default."
            )
        raise _lifecycle_error(
            current.id,
            "OCR pipeline could not be selected as default after a concurrent lifecycle change.",
        )

    async def _raise_if_record_name_conflicts(
        self,
        record: OcrPipelineDefinitionRecord,
    ) -> None:
        for name in _record_names(record):
            await self._raise_if_name_conflicts(name, excluding_pipeline_id=record.id)

    async def _raise_if_name_conflicts(
        self,
        name: str,
        *,
        excluding_pipeline_id: UUID | None = None,
    ) -> None:
        existing = await self._repository.get_by_name(name)
        if existing is None:
            return
        if excluding_pipeline_id is not None and existing.id == excluding_pipeline_id:
            return
        raise OcrPipelineAlreadyExistsError(name=name)


def _draft_definition_from_input(
    *,
    name: str,
    description: str | None,
    steps: tuple[OcrPipelineStepDefinition, ...],
) -> OcrPipelineDraftDefinition:
    try:
        return OcrPipelineDraftDefinition(
            name=name,
            description=description,
            kind=OcrPipelineKind.LINEAR,
            schema_version=1,
            steps=steps,
        )
    except ValueError as error:
        raise OcrPipelineValidationError(message=str(error)) from error


def _resolve_update[T](value: T | PreserveOcrPipelineDraftField, existing_value: T) -> T:
    if isinstance(value, PreserveOcrPipelineDraftField):
        return existing_value
    return value


def _record_names(record: OcrPipelineDefinitionRecord) -> tuple[str, ...]:
    return tuple(
        definition.name
        for definition in (record.draft, record.published_definition)
        if definition is not None
    )


def _record_display_name(record: OcrPipelineDefinitionRecord) -> str:
    names = _record_names(record)
    if names:
        return names[0]
    return str(record.id)


def _lifecycle_error(pipeline_id: UUID, message: str) -> OcrPipelineLifecycleError:
    return OcrPipelineLifecycleError(pipeline_id=pipeline_id, message=message)
