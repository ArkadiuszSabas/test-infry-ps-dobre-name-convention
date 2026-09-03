import type { ApiEnvelope } from "@/lib/api/envelope";

export type OcrPipelineRunStatus =
  | "pending"
  | "running"
  | "cancelling"
  | "succeeded"
  | "partial_failed"
  | "failed"
  | "cancelled";
export type OcrPipelineRunStepStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "skipped";
export type OcrPipelineRunDiagnosticSeverity = "error" | "warning";
export type OcrPipelineRunResultAvailability = "available" | "not_available";
export type OcrPipelineRunMetricValue = boolean | number;

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

export type PublishedOcrPipelineOptionListEnvelopeDto = ApiEnvelope<{
  pipelines: PublishedOcrPipelineOptionDto[];
}>;

export type PublishedOcrPipelineOptionListEnvelope = ApiEnvelope<{
  pipelines: PublishedOcrPipelineOption[];
}>;

export interface OcrPipelineRunErrorDto {
  code: string;
  message: string;
}

export interface OcrPipelineRunDiagnosticDto {
  severity: OcrPipelineRunDiagnosticSeverity;
  code: string;
  message: string;
  step_id: string | null;
  path: string | null;
}

export interface OcrPipelineRunStepDto {
  step_id: string;
  step_type: string;
  implementation_id: string;
  display_name: string;
  status: OcrPipelineRunStepStatus;
  duration_seconds: number | null;
  metrics: Record<string, OcrPipelineRunMetricValue>;
  error: OcrPipelineRunErrorDto | null;
}

export interface OcrPipelineRunDto {
  id: string;
  document_id: string;
  pipeline_id: string;
  pipeline_name: string | null;
  pipeline_version: number;
  status: OcrPipelineRunStatus;
  result_availability: OcrPipelineRunResultAvailability;
  result_unavailable_reason_code: string | null;
  steps: OcrPipelineRunStepDto[];
  metrics: Record<string, OcrPipelineRunMetricValue>;
  diagnostics: OcrPipelineRunDiagnosticDto[];
  error: OcrPipelineRunErrorDto | null;
  catalog_version: string | null;
  catalog_hash: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface OcrPipelineRunError {
  code: string;
  message: string;
}

export interface OcrPipelineRunDiagnostic {
  severity: OcrPipelineRunDiagnosticSeverity;
  code: string;
  message: string;
  stepId: string | null;
  path: string | null;
}

export interface OcrPipelineRunStep {
  stepId: string;
  stepType: string;
  implementationId: string;
  displayName: string;
  status: OcrPipelineRunStepStatus;
  durationSeconds: number | null;
  metrics: Record<string, OcrPipelineRunMetricValue>;
  error: OcrPipelineRunError | null;
}

export interface OcrPipelineRun {
  id: string;
  documentId: string;
  pipelineId: string;
  pipelineName: string | null;
  pipelineVersion: number;
  status: OcrPipelineRunStatus;
  resultAvailability: OcrPipelineRunResultAvailability;
  resultUnavailableReasonCode: string | null;
  steps: OcrPipelineRunStep[];
  metrics: Record<string, OcrPipelineRunMetricValue>;
  diagnostics: OcrPipelineRunDiagnostic[];
  error: OcrPipelineRunError | null;
  catalogVersion: string | null;
  catalogHash: string | null;
  createdAt: string;
  updatedAt: string;
  startedAt: string | null;
  completedAt: string | null;
}

export interface OcrPipelineRunListDto {
  runs: OcrPipelineRunDto[];
}

export interface OcrPipelineRunList {
  runs: OcrPipelineRun[];
}

export interface OcrPipelineRunListMetaDto {
  document_id: string;
  returned_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface OcrPipelineRunListMeta {
  documentId: string;
  returnedCount: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export interface OcrPipelineRunOcrPageResultDto {
  page_number: number;
  status: string;
  text: string;
  text_truncated: boolean;
  lines: string[];
  lines_truncated: boolean;
  confidence: number | null;
  warning_codes: string[];
  error_code: string | null;
  fallback_used: boolean;
  fallback_reason_codes: string[];
  primary_error_code: string | null;
}

export interface OcrPipelineRunOcrPageResult {
  pageNumber: number;
  status: string;
  text: string;
  textTruncated: boolean;
  lines: string[];
  linesTruncated: boolean;
  confidence: number | null;
  warningCodes: string[];
  errorCode: string | null;
  fallbackUsed: boolean;
  fallbackReasonCodes: string[];
  primaryErrorCode: string | null;
}

export interface OcrPipelineRunOcrResultDto {
  status: string;
  provider_id: string;
  model_id: string;
  total_page_count: number;
  succeeded_page_count: number;
  failed_page_count: number;
  average_confidence: number | null;
  low_confidence_page_count: number;
  warning_count: number;
  pages_truncated: boolean;
  pages: OcrPipelineRunOcrPageResultDto[];
}

export interface OcrPipelineRunOcrResult {
  status: string;
  providerId: string;
  modelId: string;
  totalPageCount: number;
  succeededPageCount: number;
  failedPageCount: number;
  averageConfidence: number | null;
  lowConfidencePageCount: number;
  warningCount: number;
  pagesTruncated: boolean;
  pages: OcrPipelineRunOcrPageResult[];
}

export interface OcrPipelineRunResultDto {
  run: OcrPipelineRunDto;
  result_available: boolean;
  unavailable_reason_code: string | null;
  result?: OcrPipelineRunOcrResultDto | null;
}

export interface OcrPipelineRunResult {
  run: OcrPipelineRun;
  resultAvailable: boolean;
  unavailableReasonCode: string | null;
  result: OcrPipelineRunOcrResult | null;
}

export type OcrPipelineRunEnvelopeDto = ApiEnvelope<OcrPipelineRunDto>;
export type OcrPipelineRunEnvelope = ApiEnvelope<OcrPipelineRun>;
export type OcrPipelineRunListEnvelopeDto = ApiEnvelope<
  OcrPipelineRunListDto,
  OcrPipelineRunListMetaDto
>;
export type OcrPipelineRunListEnvelope = ApiEnvelope<
  OcrPipelineRunList,
  OcrPipelineRunListMeta
>;
export type OcrPipelineRunResultEnvelopeDto =
  ApiEnvelope<OcrPipelineRunResultDto>;
export type OcrPipelineRunResultEnvelope = ApiEnvelope<OcrPipelineRunResult>;
