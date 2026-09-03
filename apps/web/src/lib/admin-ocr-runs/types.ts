import type { ApiEnvelope } from "@/lib/api/envelope";

export type AdminOcrRunView = "active" | "history";
export type OcrRunStatus =
  | "pending"
  | "running"
  | "cancelling"
  | "succeeded"
  | "partial_failed"
  | "failed"
  | "cancelled";
export type OcrRunStepStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "skipped";
export type MetricValue = boolean | number;

export interface AdminOcrRunAttemptDto {
  attempt_id: string;
  attempt_number: number;
  status: string;
  started_at: string;
  invocation_started_at: string | null;
  last_renewed_at: string;
  lease_expires_at: string;
  completed_at: string | null;
  error_code: string | null;
  execution_deadline_at: string | null;
  cancellation_deadline_at: string | null;
  last_event_sequence: number;
}

export interface AdminOcrRunSummaryDto {
  id: string;
  document_id: string;
  document_name: string;
  document_type_id: string;
  document_type_name: string;
  pipeline_id: string;
  pipeline_name: string | null;
  pipeline_version: number;
  status: OcrRunStatus;
  current_step_name: string | null;
  current_step_status: string | null;
  completed_step_count: number;
  total_step_count: number;
  started_by_actor_id: string | null;
  started_by_actor_type: string;
  started_by_actor_login: string | null;
  document_source: string | null;
  document_connector: string | null;
  connector_instance_id: string | null;
  connector_display_name: string | null;
  connector_correlation_id: string | null;
  created_at: string;
  started_at: string | null;
  updated_at: string;
  completed_at: string | null;
  latest_attempt: AdminOcrRunAttemptDto | null;
}

export interface AdminOcrRunStepDto {
  step_id: string;
  step_type: string;
  implementation_id: string;
  display_name: string;
  status: OcrRunStepStatus;
  duration_seconds: number | null;
  metrics: Record<string, MetricValue>;
  error: { code: string; message: string } | null;
}

export interface AdminOcrRunDiagnosticDto {
  severity: "error" | "warning";
  code: string;
  message: string;
  step_id: string | null;
  path: string | null;
}

export interface AdminOcrRunDetailDto {
  run: AdminOcrRunSummaryDto;
  steps: AdminOcrRunStepDto[];
  metrics: Record<string, MetricValue>;
  diagnostics: AdminOcrRunDiagnosticDto[];
  error: { code: string; message: string } | null;
  attempts: AdminOcrRunAttemptDto[];
  cancellation: {
    requested_at: string | null;
    requested_by_actor_id: string | null;
    requested_by_actor_login: string | null;
  };
}

export interface AdminOcrRunListMetaDto {
  returned_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface AdminOcrRunListFilters {
  view: AdminOcrRunView;
  status?: OcrRunStatus;
  pipelineId?: string;
  documentTypeId?: string;
  source?: string;
  connector?: string;
  createdFrom?: string;
  createdTo?: string;
  staleMs?: number;
  search?: string;
  limit: number;
  offset: number;
}

export type AdminOcrRunListEnvelope = ApiEnvelope<
  { runs: AdminOcrRunSummaryDto[] },
  AdminOcrRunListMetaDto
>;
export type AdminOcrRunDetailEnvelope = ApiEnvelope<AdminOcrRunDetailDto>;

export interface PublishedOcrPipelineOptionDto {
  id: string;
  name: string;
  published_version: number;
  is_default: boolean;
}

export interface PublishedOcrPipelineOption {
  id: string;
  name: string;
  publishedVersion: number;
  isDefault: boolean;
}

export type PublishedOcrPipelineListEnvelope = ApiEnvelope<{
  pipelines: PublishedOcrPipelineOptionDto[];
}>;
