"""Post-commit dispatch for manifest-selected approved-document handlers."""

from __future__ import annotations

import os
from importlib import import_module
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docmind_api.application.documents.ports import DocumentContentStorage
from docmind_api.domain.documents.approval import (
    DocumentApprovalStepStatus,
    DocumentApprovalWorkflowStatus,
)
from docmind_api.domain.documents.deletion import DocumentDeletionStage
from docmind_api.infrastructure.persistence.attributes.repositories import (
    SqlAlchemyAttributeDefinitionRepository,
)
from docmind_api.infrastructure.persistence.connectors.document_archive_repository import (
    SqlAlchemyConnectorDocumentArchiveRepository,
    connector_document_archive_execution_lock,
)
from docmind_api.infrastructure.persistence.connectors.repositories import (
    SqlAlchemyConnectorConfigurationRepository,
)
from docmind_api.infrastructure.persistence.document_review.repositories import (
    SqlAlchemyDocumentApprovalWorkflowRepository,
    SqlAlchemyDocumentReviewRepository,
)
from docmind_api.infrastructure.persistence.documents.deletion_repository import (
    SqlAlchemyDocumentDeletionRepository,
)
from docmind_api.infrastructure.persistence.documents.repositories import (
    SqlAlchemyDocumentRegistryRepository,
)
from docmind_api.infrastructure.persistence.sql import database_session_scope
from docmind_core.connectors import (
    ConnectorApprovedDocument,
    ConnectorApprovedDocumentCommand,
    ConnectorApprovedDocumentHandler,
    ConnectorDocumentApprovalContext,
    ConnectorDocumentArchive,
    ConnectorDocumentArchiveFailureStage,
    ConnectorDocumentArchivePlan,
    ProfileManifest,
)


class ApprovedDocumentDispatcher:
    """Revalidate a committed approval and invoke its connector-owned handler."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        storage: DocumentContentStorage,
        manifest: ProfileManifest,
    ) -> None:
        self._session_factory = session_factory
        self._storage = storage
        self._manifest = manifest

    async def __call__(self, command: ConnectorApprovedDocumentCommand) -> None:
        handler = _handler_for_instance(
            self._manifest,
            connector_instance_id=command.connector_instance_id,
        )
        if handler is None:
            return
        async with connector_document_archive_execution_lock(
            self._session_factory,
            command.document_id,
        ):
            if not await self._is_current_approval(command):
                return
            context = SqlAlchemyConnectorDocumentApprovalContext(
                session_factory=self._session_factory,
                storage=self._storage,
                manifest=self._manifest,
            )
            await handler(command, context)

    async def _is_current_approval(
        self,
        command: ConnectorApprovedDocumentCommand,
    ) -> bool:
        async with self._session_factory() as session:
            document = await SqlAlchemyDocumentRegistryRepository(session).get_by_id(
                command.document_id
            )
            workflow = await SqlAlchemyDocumentApprovalWorkflowRepository(session).get(
                command.document_id
            )
            deletion = await SqlAlchemyDocumentDeletionRepository(session).get(command.document_id)
        return (
            document is not None
            and (deletion is None or deletion.stage is DocumentDeletionStage.COMPLETED)
            and document.source.connector_instance_id == command.connector_instance_id
            and workflow is not None
            and workflow.status is DocumentApprovalWorkflowStatus.APPROVED
            and workflow.review_version == command.review_version
            and all(step.status is DocumentApprovalStepStatus.APPROVED for step in workflow.steps)
            and workflow.completed_at == command.approved_at
        )


class SqlAlchemyConnectorDocumentApprovalContext(ConnectorDocumentApprovalContext):
    """Expose short transactions and document storage to a connector handler."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        storage: DocumentContentStorage,
        manifest: ProfileManifest,
    ) -> None:
        self._session_factory = session_factory
        self._storage = storage
        self._manifest = manifest

    async def load_document(self, document_id: UUID) -> ConnectorApprovedDocument:
        async with self._session_factory() as session:
            document = await SqlAlchemyDocumentRegistryRepository(session).get_by_id(document_id)
        if document is None or document.source.connector_instance_id is None:
            raise RuntimeError("Approved connector document was not found.")
        stored = await self._storage.load(document.storage_locator)
        return ConnectorApprovedDocument(
            document_id=document.id,
            connector_instance_id=document.source.connector_instance_id,
            content=stored.content,
            metadata_values=document.metadata_values,
        )

    async def resolve_document_attribute(
        self,
        document: ConnectorApprovedDocument,
        *,
        review_version: int,
        attribute_definition_id: UUID,
    ) -> object | None:
        async with self._session_factory() as session:
            review = await SqlAlchemyDocumentReviewRepository(session).get_version(
                document.document_id,
                review_version,
            )
            review_field = (
                next(
                    (
                        field
                        for field in review.attributes
                        if field.attribute_id == attribute_definition_id
                    ),
                    None,
                )
                if review is not None
                else None
            )
            if review_field is not None:
                if review_field.value is not None:
                    return review_field.value
                metadata_key = review_field.attribute_external_id or str(attribute_definition_id)
                if metadata_key in document.metadata_values:
                    return document.metadata_values[metadata_key]
            attribute = await SqlAlchemyAttributeDefinitionRepository(session).get_by_id(
                attribute_definition_id,
            )
        if attribute is None:
            return None
        metadata_key = attribute.external_id or str(attribute.id)
        return document.metadata_values.get(metadata_key)

    async def get_configuration(self, connector_instance_id: str):
        async with self._session_factory() as session:
            configuration = await SqlAlchemyConnectorConfigurationRepository(session).get(
                connector_instance_id
            )
        return configuration.values if configuration is not None else None

    def get_secret(self, connector_instance_id: str, reference_name: str) -> str | None:
        instance = next(
            (
                item
                for item in self._manifest.connector_instances
                if item.connector_instance_id == connector_instance_id
            ),
            None,
        )
        if instance is None:
            return None
        environment_name = instance.secret_references.get(reference_name)
        if environment_name is None:
            return None
        value = os.environ.get(environment_name)
        return value if value and value.strip() else None

    async def reserve_archive(
        self,
        plan: ConnectorDocumentArchivePlan,
    ) -> ConnectorDocumentArchive:
        async with database_session_scope(self._session_factory) as session:
            return await SqlAlchemyConnectorDocumentArchiveRepository(session).reserve(plan)

    async def archive_succeeded(
        self,
        plan: ConnectorDocumentArchivePlan,
        *,
        drive_item_id: str,
        web_url: str,
    ) -> ConnectorDocumentArchive:
        async with database_session_scope(self._session_factory) as session:
            return await SqlAlchemyConnectorDocumentArchiveRepository(session).succeed(
                plan,
                drive_item_id=drive_item_id,
                web_url=web_url,
            )

    async def archive_failed(
        self,
        plan: ConnectorDocumentArchivePlan,
        *,
        error_code: str,
        failure_stage: ConnectorDocumentArchiveFailureStage,
    ) -> ConnectorDocumentArchive:
        async with database_session_scope(self._session_factory) as session:
            return await SqlAlchemyConnectorDocumentArchiveRepository(session).fail(
                plan,
                error_code=error_code,
                failure_stage=failure_stage,
            )


def _handler_for_instance(
    manifest: ProfileManifest,
    *,
    connector_instance_id: str,
) -> ConnectorApprovedDocumentHandler | None:
    instance = next(
        (
            item
            for item in manifest.connector_instances
            if item.connector_instance_id == connector_instance_id
        ),
        None,
    )
    if instance is None or instance.module_id is None:
        return None
    module = next(
        (item for item in manifest.installed_modules if item.module_id == instance.module_id),
        None,
    )
    if module is None or module.approved_document_handler_entrypoint is None:
        return None
    module_name, _separator, function_name = module.approved_document_handler_entrypoint.partition(
        ":"
    )
    handler = getattr(import_module(module_name), function_name, None)
    if not callable(handler):
        raise RuntimeError("Approved-document handler entrypoint is not callable.")
    return cast(ConnectorApprovedDocumentHandler, handler)
