"""Connector API platform context dependency factories."""

from collections.abc import Mapping
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.connectors.configuration import ConnectorConfigurationService
from docmind_api.application.connectors.document_intake import (
    ConnectorDocumentOcrStarterService,
    DocumentRegistryConnectorDocumentIntakePort,
)
from docmind_api.application.documents.ports import DocumentContentStorage
from docmind_api.application.documents.service import DocumentRegistryService
from docmind_api.application.ocr_pipeline_runs.service import OcrPipelineRunService
from docmind_api.bootstrap.dependencies.connector_configurations import (
    get_connector_configuration_service,
)
from docmind_api.bootstrap.dependencies.connectors import get_connector_profile_manifest
from docmind_api.bootstrap.dependencies.database import get_database_session
from docmind_api.bootstrap.dependencies.documents import (
    get_document_content_storage,
    get_document_ingest_settings_dependency,
    get_document_registry_service,
)
from docmind_api.bootstrap.dependencies.ocr_pipeline_runs import get_ocr_pipeline_run_service
from docmind_api.settings import DocumentIngestSettings
from docmind_core.connectors import (
    ConnectorApiPlatformContext,
    ConnectorDocumentIntakePort,
    ConnectorRouteContext,
    ProfileManifest,
)


class _ConnectorDocumentIntakeUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()


class _ConnectorConfigurationPort:
    def __init__(self, service: ConnectorConfigurationService) -> None:
        self._service = service

    async def get_values(
        self,
        route_context: ConnectorRouteContext,
    ) -> Mapping[str, str] | None:
        return await self._service.values_for_route(route_context)


def get_connector_document_intake_port(
    document_registry_service: Annotated[
        DocumentRegistryService,
        Depends(get_document_registry_service),
    ],
    document_ingest_settings: Annotated[
        DocumentIngestSettings,
        Depends(get_document_ingest_settings_dependency),
    ],
    ocr_pipeline_run_service: Annotated[
        OcrPipelineRunService,
        Depends(get_ocr_pipeline_run_service),
    ],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    storage: Annotated[
        DocumentContentStorage,
        Depends(get_document_content_storage),
    ],
) -> ConnectorDocumentIntakePort:
    """Return the in-process document intake port exposed to connector routes."""

    return DocumentRegistryConnectorDocumentIntakePort(
        document_registry_service,
        max_content_bytes=document_ingest_settings.max_content_bytes,
        ocr_starter=ConnectorDocumentOcrStarterService(
            run_service=ocr_pipeline_run_service,
            unit_of_work=_ConnectorDocumentIntakeUnitOfWork(session),
            storage=storage,
        ),
    )


def get_connector_api_platform_context(
    manifest: Annotated[ProfileManifest, Depends(get_connector_profile_manifest)],
    document_intake: Annotated[
        ConnectorDocumentIntakePort,
        Depends(get_connector_document_intake_port),
    ],
    configuration_service: Annotated[
        ConnectorConfigurationService,
        Depends(get_connector_configuration_service),
    ],
    document_ingest_settings: Annotated[
        DocumentIngestSettings,
        Depends(get_document_ingest_settings_dependency),
    ],
) -> ConnectorApiPlatformContext:
    """Return the narrow API platform context for connector route registration."""

    return ConnectorApiPlatformContext(
        manifest=manifest,
        document_intake=document_intake,
        configuration=_ConnectorConfigurationPort(configuration_service),
        max_content_bytes=document_ingest_settings.max_content_bytes,
    )
