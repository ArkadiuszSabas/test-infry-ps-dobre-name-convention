"""System catalog dependency factories for the API service."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.system_catalogs.service import SystemCatalogDefinitionService
from docmind_api.bootstrap.dependencies.database import get_database_session
from docmind_api.infrastructure.persistence.system_catalogs.repositories import (
    SqlAlchemySystemCatalogRepository,
)
from docmind_api.infrastructure.system_catalogs.runtime import (
    UtcClock,
    UuidSystemCatalogIdFactory,
)


def get_system_catalog_definition_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SystemCatalogDefinitionService:
    """Return the system catalog definition application service."""

    return SystemCatalogDefinitionService(
        repository=SqlAlchemySystemCatalogRepository(session),
        clock=UtcClock(),
        field_id_factory=UuidSystemCatalogIdFactory(),
        display_mode_id_factory=UuidSystemCatalogIdFactory(),
        display_part_id_factory=UuidSystemCatalogIdFactory(),
    )
