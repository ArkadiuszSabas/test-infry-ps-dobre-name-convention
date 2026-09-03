"""Connector platform document intake adapter."""

from typing import Protocol

from docmind_api.application.documents.commands import IngestDocumentCommand
from docmind_api.application.documents.errors import DocumentContentTooLargeError
from docmind_api.application.documents.ports import DocumentContentStorage
from docmind_api.application.documents.service import DocumentRegistryService
from docmind_api.application.documents.storage_workflow import cleanup_stored_content
from docmind_api.application.ocr_pipeline_runs.commands import StartOcrPipelineRunCommand
from docmind_api.application.ocr_pipeline_runs.service import OcrPipelineRunService
from docmind_api.domain.documents.models import DocumentRecord
from docmind_api.domain.ocr_pipeline_runs.models import OcrPipelineRunActorType
from docmind_core.connectors import (
    ConnectorDocumentIntakeRequest,
    ConnectorDocumentIntakeResult,
    ConnectorDocumentTypeExternalIdSelector,
    ConnectorRouteContext,
)


class ConnectorDocumentIntakeUnitOfWork(Protocol):
    """Commits or rolls back one connector intake unit of work."""

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class ConnectorDocumentOcrStarter(Protocol):
    """Starts connector-requested OCR after document intake."""

    async def start(self, document: DocumentRecord, *, actor_id: str) -> None: ...


class ConnectorDocumentOcrStarterService:
    """Persist one event-driven OCR run for a connector document."""

    def __init__(
        self,
        *,
        run_service: OcrPipelineRunService,
        unit_of_work: ConnectorDocumentIntakeUnitOfWork,
        storage: DocumentContentStorage,
    ) -> None:
        self._run_service = run_service
        self._unit_of_work = unit_of_work
        self._storage = storage

    async def start(self, document: DocumentRecord, *, actor_id: str) -> None:
        """Atomically commit the document and pending run before background execution."""

        try:
            await self._run_service.start_run(
                StartOcrPipelineRunCommand(
                    document_id=document.id,
                    actor_id=actor_id,
                    actor_type=OcrPipelineRunActorType.CONNECTOR,
                ),
            )
        except BaseException:
            try:
                await self._unit_of_work.rollback()
            finally:
                await cleanup_stored_content(
                    storage=self._storage,
                    document_id=document.id,
                    storage_locator=document.storage_locator,
                )
            raise
        try:
            await self._unit_of_work.commit()
        except BaseException:
            await self._unit_of_work.rollback()
            raise


class DocumentRegistryConnectorDocumentIntakePort:
    """In-process connector intake port backed by the document registry service."""

    def __init__(
        self,
        document_registry_service: DocumentRegistryService,
        *,
        max_content_bytes: int,
        ocr_starter: ConnectorDocumentOcrStarter | None = None,
    ) -> None:
        self._document_registry_service = document_registry_service
        self._max_content_bytes = max_content_bytes
        self._ocr_starter = ocr_starter

    async def ingest_document(
        self,
        route_context: ConnectorRouteContext,
        request: ConnectorDocumentIntakeRequest,
    ) -> ConnectorDocumentIntakeResult:
        """Map connector-normalized intake to the API-owned document registry use case."""

        if route_context.connector_instance_id is None:
            raise ValueError("Connector document intake requires a configured instance id.")
        if len(request.content) > self._max_content_bytes:
            raise DocumentContentTooLargeError(max_content_bytes=self._max_content_bytes)
        if request.start_ocr_pipeline and self._ocr_starter is None:
            raise RuntimeError("Connector OCR pipeline starter is not configured.")
        document_type_id = request.document_type_id
        selector = request.document_type_selector
        if isinstance(selector, ConnectorDocumentTypeExternalIdSelector):
            resolver = (
                self._document_registry_service.resolve_connector_document_type_by_external_id
            )
            document_type_id = str(
                await resolver(
                    external_id=selector.external_id,
                    parameters=selector.parameters,
                    fallback_document_type_id=selector.fallback_document_type_id,
                )
            )
        elif selector is not None:
            document_type_id = str(
                await self._document_registry_service.resolve_connector_document_type_id(
                    name=selector.name,
                    parameters=selector.parameters,
                    fallback_document_type_id=selector.fallback_document_type_id,
                )
            )
        assert document_type_id is not None
        document = await self._document_registry_service.ingest_document(
            IngestDocumentCommand(
                original_filename=request.original_filename,
                document_type_id=document_type_id,
                source=route_context.source,
                connector=route_context.connector,
                connector_instance_id=route_context.connector_instance_id,
                content=request.content,
                metadata_values=request.metadata_values,
                name=request.name,
                external_id=request.external_id,
                connector_correlation_id=request.connector_correlation_id,
                content_type=request.content_type,
            ),
        )
        if request.start_ocr_pipeline:
            assert self._ocr_starter is not None
            await self._ocr_starter.start(
                document,
                actor_id=f"connector:{route_context.connector_instance_id}",
            )
        return ConnectorDocumentIntakeResult(
            document_id=str(document.id),
            connector_instance_id=(
                document.source.connector_instance_id or route_context.connector_instance_id
            ),
        )
