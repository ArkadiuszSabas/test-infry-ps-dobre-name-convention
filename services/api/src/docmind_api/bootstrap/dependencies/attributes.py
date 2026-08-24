"""Attribute definition catalog dependency factories for the API service."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.attributes.category_service import AttributeCategoryCatalogService
from docmind_api.application.attributes.service import AttributeDefinitionCatalogService
from docmind_api.bootstrap.dependencies.database import get_database_session
from docmind_api.infrastructure.attributes.runtime import UtcClock, UuidAttributeDefinitionIdFactory
from docmind_api.infrastructure.persistence.attributes.category_repositories import (
    SqlAlchemyAttributeCategoryRepository,
    SqlAlchemyAttributeCategoryUsageRepository,
)
from docmind_api.infrastructure.persistence.attributes.repositories import (
    SqlAlchemyAttributeDefinitionRepository,
    SqlAlchemyAttributeDefinitionUsageRepository,
)
from docmind_api.infrastructure.persistence.dictionaries.repositories import (
    SqlAlchemyDictionaryRepository,
)


def get_attribute_definition_catalog_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AttributeDefinitionCatalogService:
    """Return the attribute definition catalog application service."""

    return AttributeDefinitionCatalogService(
        repository=SqlAlchemyAttributeDefinitionRepository(session),
        usage_repository=SqlAlchemyAttributeDefinitionUsageRepository(session),
        category_repository=SqlAlchemyAttributeCategoryRepository(session),
        dictionary_reference_repository=SqlAlchemyDictionaryRepository(session),
        id_factory=UuidAttributeDefinitionIdFactory(),
        clock=UtcClock(),
    )


def get_attribute_category_catalog_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AttributeCategoryCatalogService:
    """Return the system attribute category catalog application service."""

    return AttributeCategoryCatalogService(
        category_repository=SqlAlchemyAttributeCategoryRepository(session),
        category_usage_repository=SqlAlchemyAttributeCategoryUsageRepository(session),
        clock=UtcClock(),
    )
