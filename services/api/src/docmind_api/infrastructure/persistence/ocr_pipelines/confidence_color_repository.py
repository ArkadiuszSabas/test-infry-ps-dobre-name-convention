"""PostgreSQL persistence for OCR confidence color settings."""

from collections.abc import Mapping
from datetime import datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from docmind_api.domain.ocr_pipelines.confidence_colors import (
    OcrConfidenceColor,
    OcrConfidenceColorBand,
    OcrConfidenceColorSettings,
)
from docmind_api.infrastructure.persistence.ocr_pipelines.tables import (
    ocr_confidence_color_settings_table,
)

SETTINGS_KEY = "default"


class SqlAlchemyOcrConfidenceColorSettingsRepository:
    """Store the single API-owned confidence color configuration."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> OcrConfidenceColorSettings | None:
        """Return the stored configuration when an override exists."""

        row = (
            (
                await self._session.execute(
                    select(ocr_confidence_color_settings_table).where(
                        ocr_confidence_color_settings_table.c.settings_key == SETTINGS_KEY,
                    ),
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else _settings_from_row(row)

    async def save(
        self,
        settings: OcrConfidenceColorSettings,
        *,
        expected_updated_at: datetime | None,
    ) -> OcrConfidenceColorSettings | None:
        """Replace settings only when the caller still owns the loaded version."""

        if settings.updated_at is None:
            raise ValueError("Persisted OCR confidence color settings require updated_at.")

        values = {
            "schema_version": settings.schema_version,
            "bands": [
                {
                    "start": band.start,
                    "end": band.end,
                    "color": band.color.value,
                }
                for band in settings.bands
            ],
            "updated_at": settings.updated_at,
            "updated_by_actor_id": settings.updated_by_actor_id,
        }
        if expected_updated_at is None:
            statement = (
                postgresql_insert(ocr_confidence_color_settings_table)
                .values(settings_key=SETTINGS_KEY, **values)
                .on_conflict_do_nothing(
                    index_elements=[ocr_confidence_color_settings_table.c.settings_key],
                )
                .returning(ocr_confidence_color_settings_table)
            )
        else:
            statement = (
                update(ocr_confidence_color_settings_table)
                .where(
                    ocr_confidence_color_settings_table.c.settings_key == SETTINGS_KEY,
                    ocr_confidence_color_settings_table.c.updated_at == expected_updated_at,
                )
                .values(**values)
                .returning(ocr_confidence_color_settings_table)
            )
        row = (await self._session.execute(statement)).mappings().one_or_none()
        return None if row is None else _settings_from_row(row)


def _settings_from_row(row: RowMapping) -> OcrConfidenceColorSettings:
    raw_bands = cast(list[object], row["bands"])
    bands: list[OcrConfidenceColorBand] = []
    for raw_band in raw_bands:
        if not isinstance(raw_band, Mapping):
            raise ValueError("Stored OCR confidence color band must be an object.")
        band_values = cast(Mapping[str, object], raw_band)
        bands.append(
            OcrConfidenceColorBand(
                start=_integer_value(band_values.get("start"), field="start"),
                end=_integer_value(band_values.get("end"), field="end"),
                color=OcrConfidenceColor(str(band_values.get("color"))),
            ),
        )

    return OcrConfidenceColorSettings(
        schema_version=_integer_value(row["schema_version"], field="schema_version"),
        bands=tuple(bands),
        updated_at=row["updated_at"],
        updated_by_actor_id=row["updated_by_actor_id"],
    )


def _integer_value(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Stored OCR confidence color {field} must be an integer.")
    return value
