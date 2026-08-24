"""Transport mapping for OCR confidence color settings."""

from docmind_api.api.ocr_pipelines.confidence_color_schemas import (
    OcrConfidenceColorBandSchema,
    OcrConfidenceColorSettingsSchema,
)
from docmind_api.domain.ocr_pipelines.confidence_colors import OcrConfidenceColorSettings


def to_ocr_confidence_color_settings_schema(
    settings: OcrConfidenceColorSettings,
) -> OcrConfidenceColorSettingsSchema:
    """Map the domain model to the public response shape."""

    return OcrConfidenceColorSettingsSchema(
        schema_version=settings.schema_version,
        bands=[
            OcrConfidenceColorBandSchema(
                start=band.start,
                end=band.end,
                color=band.color,
            )
            for band in settings.bands
        ],
        updated_at=settings.updated_at,
    )
