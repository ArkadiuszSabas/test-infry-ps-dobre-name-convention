import { apiFetch } from "@/lib/api/client";
import { unwrapEnvelope } from "@/lib/api/envelope";

import type {
  DashboardDocumentItem,
  DashboardDocumentItemDto,
  DashboardOverview,
  DashboardOverviewEnvelopeDto,
  DashboardWindowDays,
} from "./types";

export const dashboardClient = {
  async getOverview(
    windowDays: DashboardWindowDays,
    options: { signal?: AbortSignal } = {},
  ): Promise<DashboardOverview> {
    const params = new URLSearchParams({ window_days: String(windowDays) });
    const envelope = await apiFetch<DashboardOverviewEnvelopeDto>(
      `/dashboard/overview?${params.toString()}`,
      {
        method: "GET",
        signal: options.signal,
      },
    );
    return mapDashboardOverview(unwrapEnvelope(envelope));
  },
};

export function mapDashboardOverview(
  overview: DashboardOverviewEnvelopeDto["data"],
): DashboardOverview {
  return {
    generatedAt: overview.generated_at,
    windowDays: overview.window_days,
    operationalStatus: {
      toReview: overview.operational_status.to_review,
      processing: overview.operational_status.processing,
      requiresAttention: overview.operational_status.requires_attention,
    },
    activity: overview.activity.map((day) => ({
      date: day.date,
      accepted: day.accepted,
      successfulOcr: day.successful_ocr,
      archived: day.archived,
    })),
    ocrTiming: {
      successfulSampleCount: overview.ocr_timing.successful_sample_count,
      minSeconds: overview.ocr_timing.min_seconds,
      averageSeconds: overview.ocr_timing.average_seconds,
      maxSeconds: overview.ocr_timing.max_seconds,
      weightedAverageSecondsPerPage:
        overview.ocr_timing.weighted_average_seconds_per_page,
    },
    archive: {
      total: overview.archive.total,
      addedInWindow: overview.archive.added_in_window,
    },
    toReview: overview.to_review.map(mapDocumentItem),
    requiresAttention: overview.requires_attention.map(mapDocumentItem),
  };
}

function mapDocumentItem(
  item: DashboardDocumentItemDto,
): DashboardDocumentItem {
  return {
    documentId: item.document_id,
    filename: item.filename,
    documentType: item.document_type,
    status: item.status,
    problemType: item.problem_type,
    eventAt: item.event_at,
  };
}
