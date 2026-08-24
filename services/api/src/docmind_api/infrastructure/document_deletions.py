"""Manifest-selected connector gateway for permanent document deletion."""

from importlib import import_module
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.documents.deletion_ports import (
    DocumentDeletionConnectorGateway,
)
from docmind_api.infrastructure.persistence.connectors.document_archive_repository import (
    SqlAlchemyConnectorDocumentArchiveRepository,
)
from docmind_core.connectors import (
    BUILTIN_MANUAL_UPLOAD_INSTANCE_ID,
    ConnectorDocumentArchive,
    ConnectorDocumentDeletionCommand,
    ConnectorDocumentDeletionContext,
    ConnectorDocumentDeletionHandler,
    ConnectorDocumentDeletionPolicy,
    ConnectorDocumentDeletionPreparationStatus,
    ConnectorDocumentDeletionResult,
    ProfileManifest,
)


class ManifestDocumentDeletionConnectorGateway(DocumentDeletionConnectorGateway):
    """Load only the deletion handler allowlisted for the document instance."""

    def __init__(self, *, session: AsyncSession, manifest: ProfileManifest) -> None:
        self._session = session
        self._manifest = manifest

    async def execute(
        self,
        command: ConnectorDocumentDeletionCommand,
    ) -> ConnectorDocumentDeletionResult:
        if command.connector_instance_id in {
            BUILTIN_MANUAL_UPLOAD_INSTANCE_ID,
            "manual_upload",
        }:
            return ConnectorDocumentDeletionResult(
                policy=ConnectorDocumentDeletionPolicy.NOT_APPLICABLE,
                status=ConnectorDocumentDeletionPreparationStatus.READY,
            )

        instance = next(
            (
                item
                for item in self._manifest.connector_instances
                if item.connector_instance_id == command.connector_instance_id
            ),
            None,
        )
        if instance is None or instance.module_id is None:
            return _handler_required()
        module = next(
            (
                item
                for item in self._manifest.installed_modules
                if item.module_id == instance.module_id
            ),
            None,
        )
        if module is None or module.document_deletion_handler_entrypoint is None:
            return _handler_required()

        module_name, _separator, function_name = (
            module.document_deletion_handler_entrypoint.partition(":")
        )
        try:
            handler = getattr(import_module(module_name), function_name, None)
        except ImportError, ValueError:
            return _handler_required()
        if not callable(handler):
            return _handler_required()
        context = SqlAlchemyConnectorDocumentDeletionContext(self._session)
        return await cast(ConnectorDocumentDeletionHandler, handler)(command, context)


class SqlAlchemyConnectorDocumentDeletionContext(ConnectorDocumentDeletionContext):
    """Expose only neutral archive fencing state to connector deletion handlers."""

    def __init__(self, session: AsyncSession) -> None:
        self._archives = SqlAlchemyConnectorDocumentArchiveRepository(session)

    async def get_archive(self, document_id: UUID) -> ConnectorDocumentArchive | None:
        return await self._archives.get(document_id)

    async def is_archive_active(self, document_id: UUID) -> bool:
        return await self._archives.is_execution_active(document_id)

    async def cancel_archive(
        self,
        document_id: UUID,
        *,
        error_code: str,
    ) -> ConnectorDocumentArchive | None:
        return await self._archives.cancel(document_id, error_code=error_code)


def _handler_required() -> ConnectorDocumentDeletionResult:
    return ConnectorDocumentDeletionResult(
        policy=ConnectorDocumentDeletionPolicy.BLOCK,
        status=ConnectorDocumentDeletionPreparationStatus.BLOCKED,
        error_code="DOCUMENT_DELETE_CONNECTOR_HANDLER_REQUIRED",
    )
