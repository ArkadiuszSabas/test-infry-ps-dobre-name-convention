"""Document Review initialization after an OCR pipeline terminal result."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docmind_api.application.document_review.service import DocumentReviewService
from docmind_api.infrastructure.document_review.context_resolution_source import (
    SqlAlchemyDocumentReviewPipelineSource,
)
from docmind_api.infrastructure.document_review.providers import (
    UnavailableDocumentReviewProvider,
)
from docmind_api.infrastructure.persistence.document_review.approval_settings_repository import (
    SqlAlchemyDocumentApprovalSettingsRepository,
)
from docmind_api.infrastructure.persistence.document_review.repositories import (
    SqlAlchemyDocumentApprovalWorkflowRepository,
    SqlAlchemyDocumentReviewRepository,
)
from docmind_api.infrastructure.persistence.documents.repositories import (
    SqlAlchemyDocumentRegistryRepository,
)
from docmind_api.infrastructure.persistence.sql import database_session_scope


async def initialize_pipeline_run_review(
    session_factory: async_sessionmaker[AsyncSession],
    document_id: UUID,
    run_id: UUID,
) -> None:
    """Initialize or replace Review only after a pipeline result is committed."""

    async with database_session_scope(session_factory) as session:
        document_repository = SqlAlchemyDocumentRegistryRepository(session)
        service = DocumentReviewService(
            provider=UnavailableDocumentReviewProvider(
                document_repository=document_repository,
            ),
            repository=SqlAlchemyDocumentReviewRepository(session),
            pipeline_source=SqlAlchemyDocumentReviewPipelineSource(session),
            approval_repository=SqlAlchemyDocumentApprovalWorkflowRepository(session),
            approval_settings_repository=SqlAlchemyDocumentApprovalSettingsRepository(session),
            document_repository=document_repository,
        )
        replaced = await service.replace_reprocessing_review_from_pipeline_run(document_id, run_id)
        if not replaced:
            await service.initialize_from_first_pipeline_result(document_id)
