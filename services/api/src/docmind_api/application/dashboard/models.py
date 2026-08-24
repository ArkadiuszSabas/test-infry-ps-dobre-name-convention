"""Read models returned by the operational dashboard."""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DashboardOperationalStatus:
    """Current document and OCR workload counts."""

    to_review: int
    processing: int
    requires_attention: int


@dataclass(frozen=True, slots=True)
class DashboardActivityDay:
    """One calendar day of dashboard activity."""

    date: date
    accepted: int
    successful_ocr: int
    archived: int


@dataclass(frozen=True, slots=True)
class DashboardOcrTiming:
    """Timing statistics for successful persisted OCR/parsing steps."""

    successful_sample_count: int
    min_seconds: float | None
    average_seconds: float | None
    max_seconds: float | None
    weighted_average_seconds_per_page: float | None


@dataclass(frozen=True, slots=True)
class DashboardArchiveSummary:
    """Current archive size and the selected-window increment."""

    total: int
    added_in_window: int


@dataclass(frozen=True, slots=True)
class DashboardDocumentItem:
    """Minimal document projection for an operational dashboard list."""

    document_id: UUID
    filename: str
    document_type: str | None
    status: str
    problem_type: str | None
    event_at: datetime


@dataclass(frozen=True, slots=True)
class DashboardOverview:
    """Complete snapshot rendered by the operational dashboard."""

    generated_at: datetime
    window_days: int
    operational_status: DashboardOperationalStatus
    activity: tuple[DashboardActivityDay, ...]
    ocr_timing: DashboardOcrTiming
    archive: DashboardArchiveSummary
    to_review: tuple[DashboardDocumentItem, ...]
    requires_attention: tuple[DashboardDocumentItem, ...]
