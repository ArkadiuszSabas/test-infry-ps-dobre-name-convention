"""Document type catalog dependency factories for the API service."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.document_types.service import DocumentTypeCatalogService
from docmind_api.bootstrap.dependencies.database import get_database_session
from docmind_api.infrastructure.document_types.runtime import UtcClock, UuidDocumentTypeIdFactory
from docmind_api.infrastructure.persistence.document_types.repositories import (
    SqlAlchemyDocumentTypeCatalogRepository,
    SqlAlchemyDocumentTypeUsageRepository,
)
from docmind_api.infrastructure.persistence.system_catalogs.document_type_values import (
    SqlAlchemyDocumentTypeExtensionValueRepository,
)
from docmind_api.infrastructure.system_catalogs.runtime import UuidSystemCatalogIdFactory


def get_document_type_catalog_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DocumentTypeCatalogService:
    """Return the document type catalog application service."""

    return DocumentTypeCatalogService(
        repository=SqlAlchemyDocumentTypeCatalogRepository(session),
        usage_repository=SqlAlchemyDocumentTypeUsageRepository(session),
        extension_value_repository=SqlAlchemyDocumentTypeExtensionValueRepository(session),
        extension_value_id_factory=UuidSystemCatalogIdFactory(),
        id_factory=UuidDocumentTypeIdFactory(),
        clock=UtcClock(),
    )
