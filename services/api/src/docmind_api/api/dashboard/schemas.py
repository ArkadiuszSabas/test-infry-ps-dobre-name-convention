"""Public schemas for the operational dashboard."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardOperationalStatusSchema(BaseModel):
    """Current document and OCR workload counts."""

    to_review: int = Field(ge=0)
    processing: int = Field(ge=0)
    requires_attention: int = Field(ge=0)


class DashboardActivityDaySchema(BaseModel):
    """One day in the already aggregated activity series."""

    date: date
    accepted: int = Field(ge=0)
    successful_ocr: int = Field(ge=0)
    archived: int = Field(ge=0)


class DashboardOcrTimingSchema(BaseModel):
    """Successful OCR/parsing step timing statistics."""

    successful_sample_count: int = Field(ge=0)
    min_seconds: float | None = Field(default=None, ge=0)
    average_seconds: float | None = Field(default=None, ge=0)
    max_seconds: float | None = Field(default=None, ge=0)
    weighted_average_seconds_per_page: float | None = Field(default=None, ge=0)


class DashboardArchiveSummarySchema(BaseModel):
    """Current archive size and selected-window increment."""

    total: int = Field(ge=0)
    added_in_window: int = Field(ge=0)


class DashboardDocumentItemSchema(BaseModel):
    """Minimal list item without OCR content or document attributes."""

    document_id: UUID
    filename: str
    document_type: str | None = None
    status: str
    problem_type: str | None = None
    event_at: datetime


class DashboardOverviewSchema(BaseModel):
    """Complete dashboard snapshot."""

    generated_at: datetime
    window_days: int
    operational_status: DashboardOperationalStatusSchema
    activity: list[DashboardActivityDaySchema]
    ocr_timing: DashboardOcrTimingSchema
    archive: DashboardArchiveSummarySchema
    to_review: list[DashboardDocumentItemSchema]
    requires_attention: list[DashboardDocumentItemSchema]


class DashboardOverviewMetaSchema(BaseModel):
    """Reserved dashboard response metadata."""


class DashboardOverviewEnvelope(BaseModel):
    """Standard API envelope for the dashboard snapshot."""

    data: DashboardOverviewSchema
    meta: DashboardOverviewMetaSchema = Field(default_factory=DashboardOverviewMetaSchema)
