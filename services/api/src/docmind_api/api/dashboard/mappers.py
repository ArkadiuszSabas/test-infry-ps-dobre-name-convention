"""Dashboard application-to-HTTP schema mapping."""

from docmind_api.api.dashboard.schemas import (
    DashboardActivityDaySchema,
    DashboardArchiveSummarySchema,
    DashboardDocumentItemSchema,
    DashboardOcrTimingSchema,
    DashboardOperationalStatusSchema,
    DashboardOverviewEnvelope,
    DashboardOverviewSchema,
)
from docmind_api.application.dashboard.models import (
    DashboardDocumentItem,
    DashboardOverview,
)


def to_dashboard_overview_envelope(
    overview: DashboardOverview,
) -> DashboardOverviewEnvelope:
    """Map the internal read model to the public response contract."""

    return DashboardOverviewEnvelope(
        data=DashboardOverviewSchema(
            generated_at=overview.generated_at,
            window_days=overview.window_days,
            operational_status=DashboardOperationalStatusSchema(
                to_review=overview.operational_status.to_review,
                processing=overview.operational_status.processing,
                requires_attention=overview.operational_status.requires_attention,
            ),
            activity=[
                DashboardActivityDaySchema(
                    date=day.date,
                    accepted=day.accepted,
                    successful_ocr=day.successful_ocr,
                    archived=day.archived,
                )
                for day in overview.activity
            ],
            ocr_timing=DashboardOcrTimingSchema(
                successful_sample_count=overview.ocr_timing.successful_sample_count,
                min_seconds=overview.ocr_timing.min_seconds,
                average_seconds=overview.ocr_timing.average_seconds,
                max_seconds=overview.ocr_timing.max_seconds,
                weighted_average_seconds_per_page=(
                    overview.ocr_timing.weighted_average_seconds_per_page
                ),
            ),
            archive=DashboardArchiveSummarySchema(
                total=overview.archive.total,
                added_in_window=overview.archive.added_in_window,
            ),
            to_review=[_to_document_item(item) for item in overview.to_review],
            requires_attention=[_to_document_item(item) for item in overview.requires_attention],
        ),
    )


def _to_document_item(item: DashboardDocumentItem) -> DashboardDocumentItemSchema:
    return DashboardDocumentItemSchema(
        document_id=item.document_id,
        filename=item.filename,
        document_type=item.document_type,
        status=item.status,
        problem_type=item.problem_type,
        event_at=item.event_at,
    )
