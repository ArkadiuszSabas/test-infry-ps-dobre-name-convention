"""Dependency factories for the workspace registry administration boundary."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.workspaces.ports import WorkspaceDirectoryConfiguration
from docmind_api.application.workspaces.service import WorkspaceRegistryService
from docmind_api.bootstrap.dependencies.connectors import get_connector_profile_manifest
from docmind_api.bootstrap.dependencies.database import get_database_session
from docmind_api.infrastructure.dictionaries.runtime import UtcClock
from docmind_api.infrastructure.persistence.dictionaries.repositories import (
    SqlAlchemyDictionaryRepository,
)
from docmind_api.infrastructure.persistence.workspaces.repositories import (
    SqlAlchemyWorkspaceRepository,
)
from docmind_api.infrastructure.workspaces.runtime import UuidWorkspaceIdFactory
from docmind_core.connectors.profiles import ProfileManifest


def get_workspace_directory_configuration(
    manifest: Annotated[ProfileManifest, Depends(get_connector_profile_manifest)],
) -> WorkspaceDirectoryConfiguration:
    """Map profile-owned directory settings to the application configuration port."""

    directory = manifest.workspace_directory
    if directory is None:
        return WorkspaceDirectoryConfiguration()
    return WorkspaceDirectoryConfiguration(
        dictionary_external_id=directory.dictionary_external_id,
        administration_enabled=directory.administration_enabled,
    )


def get_workspace_registry_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    configuration: Annotated[
        WorkspaceDirectoryConfiguration,
        Depends(get_workspace_directory_configuration),
    ],
) -> WorkspaceRegistryService:
    """Build the registry service with one request-scoped database transaction."""

    return WorkspaceRegistryService(
        repository=SqlAlchemyWorkspaceRepository(session),
        dictionary_repository=SqlAlchemyDictionaryRepository(session),
        configuration=configuration,
        clock=UtcClock(),
        id_factory=UuidWorkspaceIdFactory(),
    )
