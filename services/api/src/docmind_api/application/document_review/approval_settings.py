"""Application service for global document approval configuration."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from docmind_api.application.document_review.errors import (
    DocumentApprovalSettingsConflictError,
)
from docmind_api.application.document_review.ports import (
    Clock,
    DocumentApprovalSettingsRepository,
)
from docmind_api.domain.documents.approval_settings import (
    DocumentApprovalSettings,
    default_document_approval_settings,
)


@dataclass(frozen=True, slots=True)
class UpdateDocumentApprovalSettingsCommand:
    """Complete settings submitted by an administrator."""

    required_approvals: int
    actor_id: str
    expected_updated_at: datetime | None


class DocumentApprovalSettingsService:
    """Read and update API-owned document approval settings."""

    def __init__(
        self,
        *,
        repository: DocumentApprovalSettingsRepository,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._clock = clock

    async def get_settings(self) -> DocumentApprovalSettings:
        """Return persisted settings or the stable two-reviewer default."""

        settings = await self._repository.get()
        return settings or default_document_approval_settings()

    async def update_settings(
        self,
        command: UpdateDocumentApprovalSettingsCommand,
    ) -> DocumentApprovalSettings:
        """Persist settings using optimistic concurrency."""

        updated_at = self._clock.now()
        if command.expected_updated_at is not None and updated_at <= command.expected_updated_at:
            updated_at = command.expected_updated_at + timedelta(microseconds=1)
        settings = DocumentApprovalSettings(
            required_approvals=command.required_approvals,
            updated_at=updated_at,
            updated_by_actor_id=command.actor_id,
        )
        saved = await self._repository.save(
            settings,
            expected_updated_at=command.expected_updated_at,
        )
        if saved is None:
            raise DocumentApprovalSettingsConflictError()
        return saved
