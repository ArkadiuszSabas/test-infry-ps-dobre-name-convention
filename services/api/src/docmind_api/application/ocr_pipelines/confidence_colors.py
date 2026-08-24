"""Application service for OCR confidence color configuration."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from docmind_api.application.ocr_pipelines.errors import (
    OcrConfidenceColorSettingsConflictError,
    OcrPipelineValidationError,
)
from docmind_api.application.ocr_pipelines.ports import (
    Clock,
    OcrConfidenceColorSettingsRepository,
)
from docmind_api.domain.ocr_pipelines.confidence_colors import (
    OcrConfidenceColorBand,
    OcrConfidenceColorSettings,
    default_ocr_confidence_color_settings,
)


@dataclass(frozen=True, slots=True)
class UpdateOcrConfidenceColorSettingsCommand:
    """Validated values submitted by an administrator."""

    bands: tuple[OcrConfidenceColorBand, ...]
    actor_id: str | None
    expected_updated_at: datetime | None


class OcrConfidenceColorSettingsService:
    """Read and update API-owned OCR confidence presentation settings."""

    def __init__(
        self,
        *,
        repository: OcrConfidenceColorSettingsRepository,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._clock = clock

    async def get_settings(self) -> OcrConfidenceColorSettings:
        """Return persisted settings or the stable product defaults."""

        settings = await self._repository.get()
        return settings or default_ocr_confidence_color_settings()

    async def update_settings(
        self,
        command: UpdateOcrConfidenceColorSettingsCommand,
    ) -> OcrConfidenceColorSettings:
        """Validate and persist the complete confidence color configuration."""

        updated_at = self._clock.now()
        if command.expected_updated_at is not None and updated_at <= command.expected_updated_at:
            updated_at = command.expected_updated_at + timedelta(microseconds=1)

        try:
            settings = OcrConfidenceColorSettings(
                bands=command.bands,
                updated_at=updated_at,
                updated_by_actor_id=command.actor_id,
            )
        except ValueError as error:
            raise OcrPipelineValidationError(
                message=str(error),
                details={"field": "bands"},
            ) from error

        saved = await self._repository.save(
            settings,
            expected_updated_at=command.expected_updated_at,
        )
        if saved is None:
            raise OcrConfidenceColorSettingsConflictError()
        return saved
