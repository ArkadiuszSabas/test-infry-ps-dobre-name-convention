export type DashboardWindowDays = 7 | 30;

export interface DashboardOverviewDto {
  generated_at: string;
  window_days: DashboardWindowDays;
  operational_status: {
    to_review: number;
    processing: number;
    requires_attention: number;
  };
  activity: DashboardActivityDayDto[];
  ocr_timing: DashboardOcrTimingDto;
  archive: {
    total: number;
    added_in_window: number;
  };
  to_review: DashboardDocumentItemDto[];
  requires_attention: DashboardDocumentItemDto[];
}

export interface DashboardActivityDayDto {
  date: string;
  accepted: number;
  successful_ocr: number;
  archived: number;
}

export interface DashboardOcrTimingDto {
  successful_sample_count: number;
  min_seconds: number | null;
  average_seconds: number | null;
  max_seconds: number | null;
  weighted_average_seconds_per_page: number | null;
}

export interface DashboardDocumentItemDto {
  document_id: string;
  filename: string;
  document_type: string | null;
  status: string;
  problem_type: string | null;
  event_at: string;
}

export interface DashboardOverviewEnvelopeDto {
  data: DashboardOverviewDto;
  meta: Record<string, never>;
}

export interface DashboardOverview {
  generatedAt: string;
  windowDays: DashboardWindowDays;
  operationalStatus: {
    toReview: number;
    processing: number;
    requiresAttention: number;
  };
  activity: DashboardActivityDay[];
  ocrTiming: DashboardOcrTiming;
  archive: {
    total: number;
    addedInWindow: number;
  };
  toReview: DashboardDocumentItem[];
  requiresAttention: DashboardDocumentItem[];
}

export interface DashboardActivityDay {
  date: string;
  accepted: number;
  successfulOcr: number;
  archived: number;
}

export interface DashboardOcrTiming {
  successfulSampleCount: number;
  minSeconds: number | null;
  averageSeconds: number | null;
  maxSeconds: number | null;
  weightedAverageSecondsPerPage: number | null;
}

export interface DashboardDocumentItem {
  documentId: string;
  filename: string;
  documentType: string | null;
  status: string;
  problemType: string | null;
  eventAt: string;
}
