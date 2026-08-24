"""Resumable permanent document deletion orchestration."""

from dataclasses import dataclass
from uuid import UUID

from docmind_api.application.documents.deletion_ports import (
    DocumentDeletionCommitter,
    DocumentDeletionConnectorGateway,
    DocumentDeletionRepository,
)
from docmind_api.application.documents.errors import (
    DocumentDeleteAmbiguousError,
    DocumentDeleteBlockedError,
    DocumentDeleteConnectorHandlerRequiredError,
    DocumentDeleteRetryableError,
    DocumentNotFoundError,
)
from docmind_api.application.documents.ports import (
    DocumentContentStorage,
    DocumentContentStorageError,
    DocumentContentStorageNotFoundError,
)
from docmind_api.domain.documents.deletion import (
    DocumentDeletionFailureStage,
    DocumentDeletionOperation,
    DocumentDeletionStage,
)
from docmind_api.domain.documents.models import DocumentRecord, DocumentStatus
from docmind_core.connectors import (
    ConnectorDocumentDeletionCommand,
    ConnectorDocumentDeletionPhase,
    ConnectorDocumentDeletionPolicy,
    ConnectorDocumentDeletionPreparationStatus,
    ConnectorDocumentDeletionResult,
)


@dataclass(frozen=True, slots=True)
class DocumentDeletionImpact:
    """Safe confirmation payload with optional current operation state."""

    document_id: UUID
    policy: ConnectorDocumentDeletionPolicy
    preparation_status: ConnectorDocumentDeletionPreparationStatus
    warning_code: str | None
    error_code: str | None
    preserved_artifact_labels: tuple[str, ...]
    operation: DocumentDeletionOperation | None


class DocumentDeletionService:
    """Create the fence first, then resume connector, content, and DB stages."""

    def __init__(
        self,
        *,
        repository: DocumentDeletionRepository,
        connector_gateway: DocumentDeletionConnectorGateway,
        storage: DocumentContentStorage,
        committer: DocumentDeletionCommitter,
    ) -> None:
        self._repository = repository
        self._connector_gateway = connector_gateway
        self._storage = storage
        self._committer = committer

    async def get_impact(self, document_id: UUID) -> DocumentDeletionImpact:
        """Return a side-effect-free connector impact and durable operation state."""

        operation = await self._repository.get(document_id)
        document = await self._repository.get_document(document_id)
        if document is None:
            if operation is None:
                raise DocumentNotFoundError(document_id=document_id)
            return DocumentDeletionImpact(
                document_id=document_id,
                policy=operation.policy or ConnectorDocumentDeletionPolicy.NOT_APPLICABLE,
                preparation_status=ConnectorDocumentDeletionPreparationStatus.READY,
                warning_code=operation.warning_code,
                error_code=operation.error_code,
                preserved_artifact_labels=(),
                operation=operation,
            )

        try:
            result = await self._connector_gateway.execute(
                self._connector_command(document, ConnectorDocumentDeletionPhase.PLAN)
            )
        except Exception as error:
            raise DocumentDeleteRetryableError() from error
        return DocumentDeletionImpact(
            document_id=document_id,
            policy=result.policy,
            preparation_status=result.status,
            warning_code=result.warning_code,
            error_code=result.error_code,
            preserved_artifact_labels=result.preserved_artifact_labels,
            operation=operation,
        )

    async def delete(self, document_id: UUID) -> DocumentDeletionOperation:
        """Start or resume one idempotent permanent deletion operation."""

        operation = await self._repository.get(document_id)
        if operation is not None and operation.stage is DocumentDeletionStage.COMPLETED:
            return operation

        document = await self._repository.get_document(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id=document_id)

        if operation is None:
            operation = await self._repository.reserve(document)
            await self._committer.commit()

        if operation.stage is DocumentDeletionStage.REQUESTED:
            try:
                result = await self._connector_gateway.execute(
                    self._connector_command(
                        document,
                        ConnectorDocumentDeletionPhase.PREPARE,
                    )
                )
            except Exception as error:
                operation = await self._repository.fail(
                    document_id,
                    failure_stage=DocumentDeletionFailureStage.CONNECTOR,
                    error_code="DOCUMENT_DELETE_RETRYABLE",
                )
                await self._committer.commit()
                if operation.stage is DocumentDeletionStage.COMPLETED:
                    return operation
                raise DocumentDeleteRetryableError() from error
            if result.status is not ConnectorDocumentDeletionPreparationStatus.READY:
                error_code = self._public_connector_error_code(result)
                operation = await self._repository.fail(
                    document_id,
                    failure_stage=DocumentDeletionFailureStage.CONNECTOR,
                    error_code=error_code,
                    connector_result=result,
                )
                await self._committer.commit()
                if operation.stage is DocumentDeletionStage.COMPLETED:
                    return operation
                self._raise_for_connector_result(result)
            operation = await self._repository.advance(
                document_id,
                stage=DocumentDeletionStage.CONNECTOR_PREPARED,
                connector_result=result,
            )
            await self._committer.commit()

        if operation.stage is DocumentDeletionStage.CONNECTOR_PREPARED:
            try:
                await self._storage.delete(document.storage_locator)
            except DocumentContentStorageNotFoundError:
                pass
            except DocumentContentStorageError as error:
                operation = await self._repository.fail(
                    document_id,
                    failure_stage=DocumentDeletionFailureStage.CONTENT,
                    error_code="DOCUMENT_DELETE_RETRYABLE",
                )
                await self._committer.commit()
                if operation.stage is DocumentDeletionStage.COMPLETED:
                    return operation
                raise DocumentDeleteRetryableError() from error
            operation = await self._repository.advance(
                document_id,
                stage=DocumentDeletionStage.CONTENT_DELETED,
            )
            await self._committer.commit()

        if operation.stage is DocumentDeletionStage.CONTENT_DELETED:
            try:
                operation = await self._repository.purge(document_id)
                await self._committer.commit()
            except Exception as error:
                await self._committer.rollback()
                await self._repository.fail(
                    document_id,
                    failure_stage=DocumentDeletionFailureStage.DATABASE,
                    error_code="DOCUMENT_DELETE_RETRYABLE",
                )
                await self._committer.commit()
                raise DocumentDeleteRetryableError() from error

        return operation

    @staticmethod
    def _connector_command(
        document: DocumentRecord,
        phase: ConnectorDocumentDeletionPhase,
    ) -> ConnectorDocumentDeletionCommand:
        connector_instance_id = document.source.connector_instance_id or document.source.connector
        return ConnectorDocumentDeletionCommand(
            document_id=document.id,
            connector_instance_id=connector_instance_id,
            phase=phase,
            archived=document.status is DocumentStatus.APPROVED,
        )

    @staticmethod
    def _public_connector_error_code(result: ConnectorDocumentDeletionResult) -> str:
        if result.status is ConnectorDocumentDeletionPreparationStatus.BLOCKED:
            if result.error_code == "DOCUMENT_DELETE_CONNECTOR_HANDLER_REQUIRED":
                return result.error_code
            return "DOCUMENT_DELETE_BLOCKED"
        if result.status is ConnectorDocumentDeletionPreparationStatus.AMBIGUOUS:
            return "DOCUMENT_DELETE_AMBIGUOUS"
        return "DOCUMENT_DELETE_RETRYABLE"

    @staticmethod
    def _raise_for_connector_result(result: ConnectorDocumentDeletionResult) -> None:
        if result.status is ConnectorDocumentDeletionPreparationStatus.READY:
            return
        if result.error_code == "DOCUMENT_DELETE_CONNECTOR_HANDLER_REQUIRED":
            raise DocumentDeleteConnectorHandlerRequiredError()
        if result.status is ConnectorDocumentDeletionPreparationStatus.BLOCKED:
            raise DocumentDeleteBlockedError()
        if result.status is ConnectorDocumentDeletionPreparationStatus.AMBIGUOUS:
            raise DocumentDeleteAmbiguousError()
        raise DocumentDeleteRetryableError()
