"""Dependency factories for the temporary document review data source."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docmind_api.application.document_review.approval_settings import (
    DocumentApprovalSettingsService,
)
from docmind_api.application.document_review.ports import DocumentApprovalCompletionPort
from docmind_api.application.document_review.service import DocumentReviewService
from docmind_api.application.documents.ports import (
    DocumentContentStorage,
    DocumentRegistryRepository,
)
from docmind_api.bootstrap.dependencies.connectors import get_connector_profile_manifest
from docmind_api.bootstrap.dependencies.database import (
    get_database_session,
    get_database_session_factory,
)
from docmind_api.bootstrap.dependencies.documents import get_document_content_storage
from docmind_api.domain.documents.approval import DocumentApprovalWorkflow
from docmind_api.infrastructure.approved_documents import (
    ApprovedDocumentDispatcher,
)
from docmind_api.infrastructure.document_review.context_resolution_source import (
    SqlAlchemyDocumentReviewPipelineSource,
)
from docmind_api.infrastructure.document_review.providers import (
    MockDocumentReviewProvider,
    UnavailableDocumentReviewProvider,
)
from docmind_api.infrastructure.documents.runtime import UtcClock
from docmind_api.infrastructure.persistence.attribute_requirements.repositories import (
    SqlAlchemyAttributeRequirementRepository,
)
from docmind_api.infrastructure.persistence.attributes.category_repositories import (
    SqlAlchemyAttributeCategoryRepository,
)
from docmind_api.infrastructure.persistence.attributes.repositories import (
    SqlAlchemyAttributeDefinitionRepository,
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
from docmind_api.settings import get_runtime_settings
from docmind_core.connectors import ConnectorApprovedDocumentCommand, ProfileManifest


class CommittedDocumentApprovalCompletion(DocumentApprovalCompletionPort):
    """Commit the approval before invoking its manifest-selected connector handler."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        document_repository: DocumentRegistryRepository,
        dispatcher: ApprovedDocumentDispatcher,
    ) -> None:
        self._session = session
        self._document_repository = document_repository
        self._dispatcher = dispatcher

    async def complete(
        self,
        *,
        document_id: UUID,
        workflow: DocumentApprovalWorkflow,
    ) -> None:
        document = await self._document_repository.get_by_id(document_id)
        connector_instance_id = (
            document.source.connector_instance_id if document is not None else None
        )
        approved_at = workflow.completed_at
        await self._session.commit()
        if connector_instance_id is None or approved_at is None:
            return
        await self._dispatcher(
            ConnectorApprovedDocumentCommand(
                document_id=document_id,
                connector_instance_id=connector_instance_id,
                review_version=workflow.review_version,
                approved_at=approved_at,
            ),
        )


def get_document_approval_completion(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    session_factory: Annotated[
        async_sessionmaker[AsyncSession],
        Depends(get_database_session_factory),
    ],
    storage: Annotated[
        DocumentContentStorage,
        Depends(get_document_content_storage),
    ],
    manifest: Annotated[ProfileManifest, Depends(get_connector_profile_manifest)],
) -> DocumentApprovalCompletionPort:
    """Return the request commit adapter and post-commit connector dispatcher."""

    return CommittedDocumentApprovalCompletion(
        session=session,
        document_repository=SqlAlchemyDocumentRegistryRepository(session),
        dispatcher=ApprovedDocumentDispatcher(
            session_factory=session_factory,
            storage=storage,
            manifest=manifest,
        ),
    )


def get_document_type_change_review_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DocumentReviewService:
    """Return the same Review boundary used to reset a changed document type."""

    if get_runtime_settings().environment in {"local", "test", "dev"}:
        return _mock_document_review_service(session)
    return _unavailable_document_review_service(session)


def get_document_approval_settings_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> DocumentApprovalSettingsService:
    """Return the global document approval settings service."""

    return DocumentApprovalSettingsService(
        repository=SqlAlchemyDocumentApprovalSettingsRepository(session),
        clock=UtcClock(),
    )


def get_mock_document_review_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    approval_completion: Annotated[
        DocumentApprovalCompletionPort,
        Depends(get_document_approval_completion),
    ],
) -> DocumentReviewService:
    """Return a mock result provider backed by real document configuration."""

    return _mock_document_review_service(
        session,
        approval_completion=approval_completion,
    )


def _mock_document_review_service(
    session: AsyncSession,
    *,
    approval_completion: DocumentApprovalCompletionPort | None = None,
) -> DocumentReviewService:
    document_repository = SqlAlchemyDocumentRegistryRepository(session)
    return DocumentReviewService(
        provider=MockDocumentReviewProvider(
            document_repository=document_repository,
            requirement_repository=SqlAlchemyAttributeRequirementRepository(session),
            attribute_repository=SqlAlchemyAttributeDefinitionRepository(session),
            attribute_category_repository=SqlAlchemyAttributeCategoryRepository(session),
        ),
        repository=SqlAlchemyDocumentReviewRepository(session),
        pipeline_source=SqlAlchemyDocumentReviewPipelineSource(session),
        approval_repository=SqlAlchemyDocumentApprovalWorkflowRepository(session),
        approval_settings_repository=SqlAlchemyDocumentApprovalSettingsRepository(session),
        approval_completion=approval_completion,
        document_repository=document_repository,
    )


def get_unavailable_document_review_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    approval_completion: Annotated[
        DocumentApprovalCompletionPort,
        Depends(get_document_approval_completion),
    ],
) -> DocumentReviewService:
    """Return the fail-closed provider used outside approved mock environments."""

    return _unavailable_document_review_service(
        session,
        approval_completion=approval_completion,
    )


def _unavailable_document_review_service(
    session: AsyncSession,
    *,
    approval_completion: DocumentApprovalCompletionPort | None = None,
) -> DocumentReviewService:
    document_repository = SqlAlchemyDocumentRegistryRepository(session)
    return DocumentReviewService(
        provider=UnavailableDocumentReviewProvider(
            document_repository=document_repository,
        ),
        repository=SqlAlchemyDocumentReviewRepository(session),
        pipeline_source=SqlAlchemyDocumentReviewPipelineSource(session),
        approval_repository=SqlAlchemyDocumentApprovalWorkflowRepository(session),
        approval_settings_repository=SqlAlchemyDocumentApprovalSettingsRepository(session),
        approval_completion=approval_completion,
        document_repository=document_repository,
    )
