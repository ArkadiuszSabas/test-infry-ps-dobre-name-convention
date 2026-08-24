"""Framework-free OCR confidence color configuration models."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from itertools import pairwise

OCR_CONFIDENCE_COLOR_SCHEMA_VERSION = 1
OCR_CONFIDENCE_BAND_MIN_COUNT = 1
OCR_CONFIDENCE_BAND_MAX_COUNT = 5


class OcrConfidenceColor(StrEnum):
    """Supported semantic colors for OCR confidence presentation."""

    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"


def _require_integer_boundary(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("OCR confidence band boundaries must be integers.")


@dataclass(frozen=True, slots=True)
class OcrConfidenceColorBand:
    """One inclusive confidence range and its presentation color."""

    start: int
    end: int
    color: OcrConfidenceColor

    def __post_init__(self) -> None:
        _require_integer_boundary(self.start)
        _require_integer_boundary(self.end)
        if not 0 <= self.start <= 100 or not 0 <= self.end <= 100:
            raise ValueError("OCR confidence band boundaries must be between 0 and 100.")
        if self.start > self.end:
            raise ValueError("OCR confidence band start cannot exceed its end.")


@dataclass(frozen=True, slots=True)
class OcrConfidenceColorSettings:
    """Validated global confidence color configuration."""

    bands: tuple[OcrConfidenceColorBand, ...]
    schema_version: int = OCR_CONFIDENCE_COLOR_SCHEMA_VERSION
    updated_at: datetime | None = None
    updated_by_actor_id: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != OCR_CONFIDENCE_COLOR_SCHEMA_VERSION:
            raise ValueError("OCR confidence color schema_version must be 1.")

        normalized_bands = tuple(sorted(self.bands, key=lambda band: (band.start, band.end)))
        if (
            not OCR_CONFIDENCE_BAND_MIN_COUNT
            <= len(normalized_bands)
            <= (OCR_CONFIDENCE_BAND_MAX_COUNT)
        ):
            raise ValueError("OCR confidence colors require between 1 and 5 bands.")
        if normalized_bands[0].start != 0 or normalized_bands[-1].end != 100:
            raise ValueError("OCR confidence bands must cover the complete 0 to 100 range.")
        for previous, current in pairwise(normalized_bands):
            if current.start != previous.end + 1:
                raise ValueError(
                    "OCR confidence bands must not overlap or leave gaps.",
                )

        object.__setattr__(self, "bands", normalized_bands)
        if self.updated_by_actor_id is not None:
            normalized_actor_id = self.updated_by_actor_id.strip()
            if not normalized_actor_id:
                raise ValueError("OCR confidence color settings actor id cannot be blank.")
            object.__setattr__(self, "updated_by_actor_id", normalized_actor_id)


DEFAULT_OCR_CONFIDENCE_COLOR_BANDS = (
    OcrConfidenceColorBand(start=0, end=50, color=OcrConfidenceColor.RED),
    OcrConfidenceColorBand(start=51, end=75, color=OcrConfidenceColor.ORANGE),
    OcrConfidenceColorBand(start=76, end=100, color=OcrConfidenceColor.GREEN),
)


def default_ocr_confidence_color_settings() -> OcrConfidenceColorSettings:
    """Return the product default used before an administrator saves overrides."""

    return OcrConfidenceColorSettings(bands=DEFAULT_OCR_CONFIDENCE_COLOR_BANDS)
