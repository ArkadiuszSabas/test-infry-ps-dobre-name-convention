"""OCR pipeline run application use cases."""

from collections.abc import Mapping
from uuid import UUID

from docmind_api.application.documents.errors import DocumentArchivedError
from docmind_api.application.ocr_pipeline_runs.commands import (
    GetOcrPipelineRunQuery,
    ListDocumentOcrPipelineRunsQuery,
    StartOcrPipelineRunCommand,
)
from docmind_api.application.ocr_pipeline_runs.context_resolver_config import (
    OcrPipelineContextAttributeSource,
    compiled_snapshot_with_context_attributes,
)
from docmind_api.application.ocr_pipeline_runs.errors import (
    OcrPipelineRunAlreadyActiveError,
    OcrPipelineRunDocumentNotFoundError,
    OcrPipelineRunLimitExceededError,
    OcrPipelineRunNoPublishedPipelineError,
    OcrPipelineRunNotFoundError,
    OcrPipelineRunPipelineNotRunnableError,
    OcrPipelineRunUnknownDocumentSizeError,
    OcrPipelineRunValidationError,
)
from docmind_api.application.ocr_pipeline_runs.ports import (
    Clock,
    DirectOcrPipelineRunLimits,
    OcrPipelineRunDocumentReader,
    OcrPipelineRunIdFactory,
    OcrPipelineRunInvoker,
    OcrPipelineRunRepository,
    PublishedOcrPipelineSnapshotReader,
)
from docmind_api.domain.ocr_pipeline_runs.models import (
    JsonObject,
    OcrPipelineRunDocument,
    OcrPipelineRunList,
    OcrPipelineRunRecord,
    OcrPipelineRunStatus,
    pending_steps_from_compiled_snapshot,
)


class OcrPipelineRunService:
    """Application service for direct OCR pipeline run contracts."""

    def __init__(
        self,
        *,
        repository: OcrPipelineRunRepository,
        document_reader: OcrPipelineRunDocumentReader,
        pipeline_reader: PublishedOcrPipelineSnapshotReader,
        invoker: OcrPipelineRunInvoker,
        id_factory: OcrPipelineRunIdFactory,
        clock: Clock,
        limits: DirectOcrPipelineRunLimits,
        context_attribute_source: OcrPipelineContextAttributeSource | None = None,
        connector_display_names: Mapping[str, str] | None = None,
    ) -> None:
        self._repository = repository
        self._document_reader = document_reader
        self._pipeline_reader = pipeline_reader
        self._invoker = invoker
        self._id_factory = id_factory
        self._clock = clock
        self._limits = limits
        self._context_attribute_source = context_attribute_source
        self._connector_display_names = dict(connector_display_names or {})

    async def start_run(self, command: StartOcrPipelineRunCommand) -> OcrPipelineRunRecord:
        """Create a pending run against the default published pipeline snapshot."""

        document = await self._document_reader.get_run_document(command.document_id)
        if document is None:
            raise OcrPipelineRunDocumentNotFoundError(document_id=command.document_id)
        if document.is_archived:
            raise DocumentArchivedError(document_id=command.document_id)

        active_run = await self._repository.get_active_by_document_id(document.id)
        if active_run is not None:
            raise OcrPipelineRunAlreadyActiveError(document_id=document.id, run_id=active_run.id)

        if document.content_size_bytes is None:
            raise OcrPipelineRunUnknownDocumentSizeError(document_id=document.id)
        if document.content_size_bytes > self._limits.max_content_bytes:
            raise OcrPipelineRunLimitExceededError(
                document_id=document.id,
                content_size_bytes=document.content_size_bytes,
                max_content_bytes=self._limits.max_content_bytes,
            )

        pipeline = await self._pipeline_reader.get_default_published()
        if pipeline is None:
            raise OcrPipelineRunNoPublishedPipelineError()

        try:
            compiled_snapshot = await self._compiled_snapshot_for_document(
                pipeline.compiled_snapshot,
                document_type_id=document.document_type_id,
                metadata_values=document.metadata_values,
            )
            steps = pending_steps_from_compiled_snapshot(
                compiled_snapshot,
                max_step_count=self._limits.max_step_count,
            )
        except ValueError as error:
            raise OcrPipelineRunPipelineNotRunnableError(
                pipeline_id=pipeline.pipeline_id,
                reason=str(error),
            ) from error

        timestamp = self._clock.now()
        record = OcrPipelineRunRecord(
            id=self._id_factory.new_id(),
            document_id=document.id,
            pipeline_id=pipeline.pipeline_id,
            pipeline_version=pipeline.pipeline_version,
            document_reference=document.storage_locator,
            compiled_snapshot=compiled_snapshot,
            status=OcrPipelineRunStatus.PENDING,
            steps=steps,
            metrics={"document_size_bytes": document.content_size_bytes},
            diagnostics=(),
            catalog_version=pipeline.catalog_version,
            catalog_hash=pipeline.catalog_hash,
            pipeline_name=pipeline.pipeline_name,
            created_at=timestamp,
            updated_at=timestamp,
            started_by_actor_id=command.actor_id,
            started_by_actor_type=command.actor_type,
            started_by_actor_login=command.actor_login,
            document_source=document.source,
            document_connector=document.connector,
            connector_instance_id=document.connector_instance_id,
            connector_display_name=self._connector_display_name(document),
            connector_correlation_id=document.connector_correlation_id,
        )
        created = await self._repository.add(record)
        if not created:
            active_run = await self._repository.get_active_by_document_id(document.id)
            if active_run is not None:
                raise OcrPipelineRunAlreadyActiveError(
                    document_id=document.id,
                    run_id=active_run.id,
                )
            raise OcrPipelineRunValidationError(message="OCR pipeline run could not be created.")
        return record

    def _connector_display_name(self, document: OcrPipelineRunDocument) -> str | None:
        if document.connector_instance_id is not None:
            display_name = self._connector_display_names.get(document.connector_instance_id)
            if display_name is not None:
                return display_name
        return document.connector

    async def get_run(self, query: GetOcrPipelineRunQuery) -> OcrPipelineRunRecord:
        """Return one OCR pipeline run."""

        return await self._get_run(query.run_id)

    async def _compiled_snapshot_for_document(
        self,
        compiled_snapshot: JsonObject,
        *,
        document_type_id: UUID,
        metadata_values: JsonObject,
    ) -> JsonObject:
        if self._context_attribute_source is None:
            return compiled_snapshot
        return await compiled_snapshot_with_context_attributes(
            compiled_snapshot,
            document_type_id=document_type_id,
            metadata_values=metadata_values,
            attribute_source=self._context_attribute_source,
        )

    async def list_document_runs(
        self,
        query: ListDocumentOcrPipelineRunsQuery,
    ) -> OcrPipelineRunList:
        """Return recent OCR pipeline runs for a document."""

        if query.limit < 1 or query.limit > 100:
            raise OcrPipelineRunValidationError(
                message="OCR pipeline run list limit must be between 1 and 100.",
                details={"limit": query.limit, "max_limit": 100},
            )
        if query.offset < 0:
            raise OcrPipelineRunValidationError(
                message="OCR pipeline run list offset cannot be negative.",
                details={"offset": query.offset},
            )
        return await self._repository.list_by_document_id(
            query.document_id,
            limit=query.limit,
            offset=query.offset,
        )

    async def _get_run(self, run_id: UUID | str) -> OcrPipelineRunRecord:
        record = await self._repository.get_by_id(run_id)
        if record is None:
            raise OcrPipelineRunNotFoundError(run_id=run_id)
        return record
