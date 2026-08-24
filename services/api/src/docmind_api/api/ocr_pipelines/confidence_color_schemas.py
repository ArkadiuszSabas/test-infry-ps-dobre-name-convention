"""HTTP schemas for global OCR confidence color settings."""

from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from docmind_api.domain.ocr_pipelines.confidence_colors import (
    OCR_CONFIDENCE_BAND_MAX_COUNT,
    OCR_CONFIDENCE_BAND_MIN_COUNT,
    OcrConfidenceColor,
    OcrConfidenceColorBand,
    OcrConfidenceColorSettings,
)

ConfidenceBoundary = Annotated[int, Field(strict=True, ge=0, le=100)]


class OcrConfidenceColorBandSchema(BaseModel):
    """One inclusive confidence range."""

    model_config = ConfigDict(extra="forbid")

    start: ConfidenceBoundary
    end: ConfidenceBoundary
    color: OcrConfidenceColor


class UpdateOcrConfidenceColorSettingsRequest(BaseModel):
    """Complete confidence color configuration submitted by an administrator."""

    model_config = ConfigDict(extra="forbid")

    bands: list[OcrConfidenceColorBandSchema] = Field(
        min_length=OCR_CONFIDENCE_BAND_MIN_COUNT,
        max_length=OCR_CONFIDENCE_BAND_MAX_COUNT,
    )
    expected_updated_at: datetime | None

    @model_validator(mode="after")
    def validate_complete_coverage(self) -> Self:
        """Reject gaps, overlaps, inverted ranges, and incomplete coverage."""

        OcrConfidenceColorSettings(
            bands=tuple(
                OcrConfidenceColorBand(
                    start=band.start,
                    end=band.end,
                    color=band.color,
                )
                for band in self.bands
            ),
        )
        return self


class OcrConfidenceColorSettingsSchema(BaseModel):
    """Read model returned to administrators and document reviewers."""

    schema_version: int
    bands: list[OcrConfidenceColorBandSchema]
    updated_at: datetime | None


class OcrConfidenceColorSettingsEnvelope(BaseModel):
    """Standard Product API envelope."""

    data: OcrConfidenceColorSettingsSchema
    meta: dict[str, str] = Field(default_factory=dict)
