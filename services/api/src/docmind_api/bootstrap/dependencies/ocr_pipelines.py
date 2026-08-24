"""OCR pipeline admin dependency factories for the API service."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.application.ocr_pipelines.confidence_colors import (
    OcrConfidenceColorSettingsService,
)
from docmind_api.application.ocr_pipelines.service import OcrPipelineAdminService
from docmind_api.bootstrap.dependencies.database import get_database_session
from docmind_api.infrastructure.ocr_pipelines.llmmagic_dapr import (
    DaprLlmMagicOcrPipelineBlockCatalogClient,
)
from docmind_api.infrastructure.ocr_pipelines.runtime import UtcClock, UuidOcrPipelineIdFactory
from docmind_api.infrastructure.persistence.attributes.repositories import (
    SqlAlchemyAttributeDefinitionRepository,
)
from docmind_api.infrastructure.persistence.document_types.repositories import (
    SqlAlchemyDocumentTypeCatalogRepository,
)
from docmind_api.infrastructure.persistence.ocr_pipelines.confidence_color_repository import (
    SqlAlchemyOcrConfidenceColorSettingsRepository,
)
from docmind_api.infrastructure.persistence.ocr_pipelines.repositories import (
    SqlAlchemyOcrPipelineDefinitionRepository,
)
from docmind_api.settings import get_dapr_client_settings
from docmind_backend_runtime import create_dapr_client


def get_ocr_pipeline_admin_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> OcrPipelineAdminService:
    """Return the OCR pipeline admin application service."""

    return OcrPipelineAdminService(
        repository=SqlAlchemyOcrPipelineDefinitionRepository(session),
        block_catalog_client=DaprLlmMagicOcrPipelineBlockCatalogClient(
            dapr_client=create_dapr_client(get_dapr_client_settings()),
        ),
        document_type_reference_catalog=SqlAlchemyDocumentTypeCatalogRepository(session),
        attribute_reference_catalog=SqlAlchemyAttributeDefinitionRepository(session),
        id_factory=UuidOcrPipelineIdFactory(),
        clock=UtcClock(),
    )


def get_ocr_confidence_color_settings_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> OcrConfidenceColorSettingsService:
    """Return the global OCR confidence color settings service."""

    return OcrConfidenceColorSettingsService(
        repository=SqlAlchemyOcrConfidenceColorSettingsRepository(session),
        clock=UtcClock(),
    )
