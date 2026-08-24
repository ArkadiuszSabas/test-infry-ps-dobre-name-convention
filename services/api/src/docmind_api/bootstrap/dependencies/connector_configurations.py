"""Dependency factories for durable connector instance configuration."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.connectors.configuration import ConnectorConfigurationService
from docmind_api.bootstrap.dependencies.connectors import get_connector_profile_manifest
from docmind_api.bootstrap.dependencies.database import (
    get_database_engine,
    get_database_session,
    get_database_session_factory,
)
from docmind_api.infrastructure.persistence.attributes.repositories import (
    SqlAlchemyAttributeDefinitionRepository,
)
from docmind_api.infrastructure.persistence.connectors.repositories import (
    SqlAlchemyConnectorConfigurationRepository,
)
from docmind_api.infrastructure.persistence.sql import database_session_scope
from docmind_api.settings import get_database_settings
from docmind_core.connectors import ProfileManifest


def get_connector_configuration_service(
    manifest: Annotated[ProfileManifest, Depends(get_connector_profile_manifest)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ConnectorConfigurationService:
    """Return the API-owned service for the active profile's connector instances."""

    return ConnectorConfigurationService(
        manifest=manifest,
        repository=SqlAlchemyConnectorConfigurationRepository(session),
        attribute_repository=SqlAlchemyAttributeDefinitionRepository(session),
    )


async def get_optional_connector_configuration_service(
    request: Request,
    manifest: Annotated[ProfileManifest, Depends(get_connector_profile_manifest)],
) -> AsyncGenerator[ConnectorConfigurationService | None]:
    """Yield saved configuration when database settings are available.

    Connector routes can still use their deployment-secret fallback in lightweight
    application tests and bootstrap diagnostics that deliberately have no database.
    """

    try:
        settings = get_database_settings()
    except RuntimeError:
        yield None
        return

    engine = get_database_engine(request, settings)
    session_factory = get_database_session_factory(request, engine)
    async with database_session_scope(session_factory) as session:
        yield ConnectorConfigurationService(
            manifest=manifest,
            repository=SqlAlchemyConnectorConfigurationRepository(session),
            attribute_repository=SqlAlchemyAttributeDefinitionRepository(session),
        )
