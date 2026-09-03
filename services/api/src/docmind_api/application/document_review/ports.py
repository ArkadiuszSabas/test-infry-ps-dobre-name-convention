"""Application ports for document review state."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from docmind_api.application.document_review.read_models import (
    DocumentReviewHistoryItem,
    DocumentReviewResult,
)
from docmind_api.domain.documents.approval import (
    DocumentApprovalDecision,
    DocumentApprovalWorkflow,
)
from docmind_api.domain.documents.approval_settings import DocumentApprovalSettings


class Clock(Protocol):
    """Returns timezone-aware timestamps."""

    def now(self) -> datetime: ...


class DocumentApprovalSettingsRepository(Protocol):
    """Persists the global document approval configuration."""

    async def get(self) -> DocumentApprovalSettings | None: ...

    async def save(
        self,
        settings: DocumentApprovalSettings,
        *,
        expected_updated_at: datetime | None,
    ) -> DocumentApprovalSettings | None: ...


class DocumentReviewProvider(Protocol):
    """Provides a review projection without exposing its source to the route."""

    async def get_review(self, document_id: UUID) -> DocumentReviewResult: ...


class DocumentReviewPipelineSource(Protocol):
    """Provides the oldest eligible pipeline projection for Review initialization."""

    async def get_first_eligible(self, document_id: UUID) -> DocumentReviewResult | None: ...

    async def get_for_run(
        self,
        document_id: UUID,
        run_id: UUID,
    ) -> DocumentReviewResult | None: ...


class DocumentReviewRepository(Protocol):
    """Persists immutable Review snapshots and the current-version pointer."""

    async def get_current(self, document_id: UUID) -> DocumentReviewResult | None: ...

    async def get_version(self, document_id: UUID, version: int) -> DocumentReviewResult | None: ...

    async def get_latest_source_pipeline_run_id(
        self,
        document_id: UUID,
        *,
        before_version: int,
    ) -> UUID | None: ...

    async def list_history(
        self,
        document_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[DocumentReviewHistoryItem, ...]: ...

    async def initialize(self, result: DocumentReviewResult) -> bool: ...

    async def save_next(
        self,
        *,
        result: DocumentReviewResult,
        expected_version: int,
    ) -> bool: ...

    async def save_pipeline_source_hydration(self, result: DocumentReviewResult) -> bool: ...


class DocumentApprovalWorkflowRepository(Protocol):
    """Persists current approval state and append-only decision history."""

    async def get(self, document_id: UUID) -> DocumentApprovalWorkflow | None: ...

    async def initialize(
        self,
        document_id: UUID,
        *,
        required_approvals: int = 2,
    ) -> DocumentApprovalWorkflow: ...

    async def reset_for_review_version(
        self, *, document_id: UUID, review_version: int
    ) -> DocumentApprovalWorkflow: ...

    async def decide(
        self,
        *,
        document_id: UUID,
        actor_id: str,
        expected_review_version: int,
        decision: DocumentApprovalDecision,
        comment: str | None,
    ) -> DocumentApprovalWorkflow: ...


class DocumentApprovalCompletionPort(Protocol):
    """Commits and dispatches side effects after a completed approval workflow."""

    async def complete(
        self,
        *,
        document_id: UUID,
        workflow: DocumentApprovalWorkflow,
    ) -> None: ...
