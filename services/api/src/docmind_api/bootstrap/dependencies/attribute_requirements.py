"""Attribute requirement matrix dependency factories for the API service."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.attribute_requirements.service import (
    AttributeRequirementMatrixService,
)
from docmind_api.bootstrap.dependencies.database import get_database_session
from docmind_api.infrastructure.attribute_requirements.runtime import (
    UtcClock,
    UuidAttributeRequirementIdFactory,
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
from docmind_api.infrastructure.persistence.document_types.repositories import (
    SqlAlchemyDocumentTypeCatalogRepository,
)


def get_attribute_requirement_matrix_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AttributeRequirementMatrixService:
    """Return the attribute requirement matrix application service."""

    return AttributeRequirementMatrixService(
        repository=SqlAlchemyAttributeRequirementRepository(session),
        document_type_repository=SqlAlchemyDocumentTypeCatalogRepository(session),
        attribute_repository=SqlAlchemyAttributeDefinitionRepository(session),
        attribute_category_repository=SqlAlchemyAttributeCategoryRepository(session),
        id_factory=UuidAttributeRequirementIdFactory(),
        clock=UtcClock(),
    )
