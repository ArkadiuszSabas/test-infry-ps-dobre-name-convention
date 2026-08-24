"""Document registry dependency factories for the API service."""

from inspect import isawaitable
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.documents.deletion_ports import DocumentDeletionCommitter
from docmind_api.application.documents.deletion_service import DocumentDeletionService
from docmind_api.application.documents.ports import DocumentContentStorage
from docmind_api.application.documents.service import DocumentRegistryService
from docmind_api.bootstrap.dependencies.connectors import get_connector_profile_manifest
from docmind_api.bootstrap.dependencies.database import get_database_session
from docmind_api.infrastructure.document_deletions import (
    ManifestDocumentDeletionConnectorGateway,
)
from docmind_api.infrastructure.documents.runtime import UtcClock, UuidDocumentIdFactory
from docmind_api.infrastructure.documents.storage import (
    AzureBlobDocumentStorageClient,
    AzureSdkBlobClientFactory,
    FilesystemDocumentContentStorage,
)
from docmind_api.infrastructure.persistence.attribute_requirements.repositories import (
    SqlAlchemyAttributeRequirementRepository,
)
from docmind_api.infrastructure.persistence.attributes.category_repositories import (
    SqlAlchemyAttributeCategoryRepository,
)
from docmind_api.infrastructure.persistence.attributes.repositories import (
    SqlAlchemyAttributeDefinitionRepository,
)
from docmind_api.infrastructure.persistence.connectors.document_archive_repository import (
    SqlAlchemyConnectorDocumentArchiveRepository,
)
from docmind_api.infrastructure.persistence.dictionaries.repositories import (
    SqlAlchemyDictionaryRepository,
)
from docmind_api.infrastructure.persistence.document_types.repositories import (
    SqlAlchemyDocumentTypeCatalogRepository,
)
from docmind_api.infrastructure.persistence.documents.deletion_repository import (
    SqlAlchemyDocumentDeletionRepository,
)
from docmind_api.infrastructure.persistence.documents.repositories import (
    SqlAlchemyDocumentRegistryRepository,
)
from docmind_api.settings import (
    DocumentIngestSettings,
    DocumentStorageProvider,
    DocumentStorageSettings,
    load_document_ingest_settings,
    load_document_storage_settings,
)
from docmind_core.connectors import ProfileManifest

_DOCUMENT_CONTENT_STORAGE_STATE_KEY = "document_content_storage"


class DocumentTypeChangeCommitter:
    """Infrastructure transaction adapter for document type changes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()


class SqlAlchemyDocumentDeletionCommitter(DocumentDeletionCommitter):
    """Commit or roll back one request-scoped deletion stage."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()


def get_document_type_change_committer(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DocumentTypeChangeCommitter:
    """Return the request transaction committer for a completed type change."""

    return DocumentTypeChangeCommitter(session)


def get_document_storage_settings_dependency() -> DocumentStorageSettings:
    """Return document storage settings for dependency injection."""

    return load_document_storage_settings()


def get_document_ingest_settings_dependency() -> DocumentIngestSettings:
    """Return document ingest settings for dependency injection."""

    return load_document_ingest_settings()


def get_document_content_storage(
    request: Request,
    storage_settings: Annotated[
        DocumentStorageSettings,
        Depends(get_document_storage_settings_dependency),
    ],
) -> DocumentContentStorage:
    """Return the app-scoped document content storage adapter."""

    storage = getattr(request.app.state, _DOCUMENT_CONTENT_STORAGE_STATE_KEY, None)
    if storage is None:
        storage = _create_document_content_storage(storage_settings)
        setattr(request.app.state, _DOCUMENT_CONTENT_STORAGE_STATE_KEY, storage)

    return storage


def get_document_registry_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[
        DocumentContentStorage,
        Depends(get_document_content_storage),
    ],
) -> DocumentRegistryService:
    """Return the document registry application service."""

    return DocumentRegistryService(
        repository=SqlAlchemyDocumentRegistryRepository(session),
        document_type_repository=SqlAlchemyDocumentTypeCatalogRepository(session),
        attribute_repository=SqlAlchemyAttributeDefinitionRepository(session),
        attribute_category_repository=SqlAlchemyAttributeCategoryRepository(session),
        requirement_repository=SqlAlchemyAttributeRequirementRepository(session),
        dictionary_repository=SqlAlchemyDictionaryRepository(session),
        storage=storage,
        id_factory=UuidDocumentIdFactory(),
        clock=UtcClock(),
        archive_repository=SqlAlchemyConnectorDocumentArchiveRepository(session),
    )


def get_document_deletion_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[DocumentContentStorage, Depends(get_document_content_storage)],
    manifest: Annotated[ProfileManifest, Depends(get_connector_profile_manifest)],
) -> DocumentDeletionService:
    """Return the resumable permanent document deletion use case."""

    return DocumentDeletionService(
        repository=SqlAlchemyDocumentDeletionRepository(session),
        connector_gateway=ManifestDocumentDeletionConnectorGateway(
            session=session,
            manifest=manifest,
        ),
        storage=storage,
        committer=SqlAlchemyDocumentDeletionCommitter(session),
    )


def _create_document_content_storage(
    settings: DocumentStorageSettings,
) -> FilesystemDocumentContentStorage | AzureBlobDocumentStorageClient:
    if settings.provider == DocumentStorageProvider.FILESYSTEM:
        return FilesystemDocumentContentStorage(settings.root_path)

    if settings.azure_container_name is None:
        raise RuntimeError("Azure Blob document storage requires a container name.")

    return AzureBlobDocumentStorageClient(
        container_name=settings.azure_container_name,
        blob_prefix=settings.azure_blob_prefix,
        client_factory=AzureSdkBlobClientFactory(
            account_url=settings.azure_account_url,
            connection_string=settings.azure_connection_string,
            container_name=settings.azure_container_name,
            network_timeout_seconds=settings.azure_operation_timeout_seconds,
        ),
        operation_timeout_seconds=settings.azure_operation_timeout_seconds,
    )


async def dispose_document_content_storage(app: FastAPI) -> None:
    """Close app-scoped document content storage resources."""

    storage = getattr(app.state, _DOCUMENT_CONTENT_STORAGE_STATE_KEY, None)
    close = getattr(storage, "close", None)
    if callable(close):
        close_result = close()
        if isawaitable(close_result):
            await close_result

    setattr(app.state, _DOCUMENT_CONTENT_STORAGE_STATE_KEY, None)
