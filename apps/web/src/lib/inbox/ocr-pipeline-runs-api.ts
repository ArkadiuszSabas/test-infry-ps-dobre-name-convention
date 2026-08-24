import { apiFetch } from "@/lib/api/client";
import { unwrapEnvelope } from "@/lib/api/envelope";

import type {
  OcrPipelineRun,
  OcrPipelineRunDto,
  OcrPipelineRunEnvelopeDto,
  OcrPipelineRunListEnvelope,
  OcrPipelineRunListEnvelopeDto,
  OcrPipelineRunOcrPageResult,
  OcrPipelineRunOcrPageResultDto,
  OcrPipelineRunOcrResult,
  OcrPipelineRunOcrResultDto,
  OcrPipelineRunResult,
  OcrPipelineRunResultDto,
  OcrPipelineRunResultEnvelope,
  OcrPipelineRunResultEnvelopeDto,
} from "./types";

export const OCR_PIPELINE_RUN_HISTORY_LIMIT = 5;
const OCR_PIPELINE_RUN_LIST_LIMIT = 10;

interface OcrPipelineRunRequestOptions {
  signal?: AbortSignal;
  csrfToken?: string | null;
}

export interface OcrPipelineRunListRequestOptions extends OcrPipelineRunRequestOptions {
  limit?: number;
  offset?: number;
}

export const ocrPipelineRunClient = {
  async startDocumentOcrPipelineRun(
    documentId: string,
    options: OcrPipelineRunRequestOptions = {},
  ): Promise<OcrPipelineRun> {
    return mapOcrPipelineRun(
      unwrapEnvelope(
        await apiFetch<OcrPipelineRunEnvelopeDto>(
          `/documents/${encodeURIComponent(documentId)}/ocr/pipeline-runs`,
          {
            csrfToken: options.csrfToken,
            method: "POST",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async listDocumentOcrPipelineRuns(
    documentId: string,
    options: OcrPipelineRunListRequestOptions = {},
  ): Promise<OcrPipelineRunListEnvelope> {
    const params = new URLSearchParams({
      limit: String(options.limit ?? OCR_PIPELINE_RUN_LIST_LIMIT),
      offset: String(options.offset ?? 0),
    });

    return mapOcrPipelineRunListEnvelope(
      await apiFetch<OcrPipelineRunListEnvelopeDto>(
        `/documents/${encodeURIComponent(documentId)}/ocr/pipeline-runs?${params.toString()}`,
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async getOcrPipelineRun(
    runId: string,
    options: OcrPipelineRunRequestOptions = {},
  ): Promise<OcrPipelineRun> {
    return mapOcrPipelineRun(
      unwrapEnvelope(
        await apiFetch<OcrPipelineRunEnvelopeDto>(
          `/ocr/pipeline-runs/${encodeURIComponent(runId)}`,
          {
            method: "GET",
            signal: options.signal,
          },
        ),
      ),
    );
  },

  async getOcrPipelineRunResult(
    runId: string,
    options: OcrPipelineRunRequestOptions = {},
  ): Promise<OcrPipelineRunResultEnvelope> {
    return mapOcrPipelineRunResultEnvelope(
      await apiFetch<OcrPipelineRunResultEnvelopeDto>(
        `/ocr/pipeline-runs/${encodeURIComponent(runId)}/result`,
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },

  async loadOcrPipelineRunResult(
    runId: string,
    options: OcrPipelineRunRequestOptions = {},
  ): Promise<OcrPipelineRunResultEnvelope> {
    return mapOcrPipelineRunResultEnvelope(
      await apiFetch<OcrPipelineRunResultEnvelopeDto>(
        `/ocr/pipeline-runs/${encodeURIComponent(runId)}/result`,
        {
          method: "GET",
          signal: options.signal,
        },
      ),
    );
  },
};

function mapOcrPipelineRunListEnvelope(
  envelope: OcrPipelineRunListEnvelopeDto,
): OcrPipelineRunListEnvelope {
  return {
    data: {
      runs: envelope.data.runs.map(mapOcrPipelineRun),
    },
    meta: {
      documentId: envelope.meta.document_id,
      hasMore: envelope.meta.has_more,
      limit: envelope.meta.limit,
      offset: envelope.meta.offset,
      returnedCount: envelope.meta.returned_count,
    },
  };
}

function mapOcrPipelineRunResultEnvelope(
  envelope: OcrPipelineRunResultEnvelopeDto,
): OcrPipelineRunResultEnvelope {
  return {
    data: mapOcrPipelineRunResult(envelope.data),
    meta: envelope.meta,
  };
}

function mapOcrPipelineRunResult(
  result: OcrPipelineRunResultDto,
): OcrPipelineRunResult {
  return {
    result: result.result ? mapOcrPipelineRunOcrResult(result.result) : null,
    resultAvailable: result.result_available,
    run: mapOcrPipelineRun(result.run),
    unavailableReasonCode: result.unavailable_reason_code,
  };
}

function mapOcrPipelineRun(run: OcrPipelineRunDto): OcrPipelineRun {
  return {
    catalogHash: run.catalog_hash,
    catalogVersion: run.catalog_version,
    completedAt: run.completed_at,
    createdAt: run.created_at,
    diagnostics: run.diagnostics.map((diagnostic) => ({
      code: diagnostic.code,
      message: diagnostic.message,
      path: diagnostic.path,
      severity: diagnostic.severity,
      stepId: diagnostic.step_id,
    })),
    documentId: run.document_id,
    error: run.error
      ? { code: run.error.code, message: run.error.message }
      : null,
    id: run.id,
    metrics: run.metrics,
    pipelineId: run.pipeline_id,
    pipelineName: run.pipeline_name,
    pipelineVersion: run.pipeline_version,
    resultAvailability: run.result_availability,
    resultUnavailableReasonCode: run.result_unavailable_reason_code,
    startedAt: run.started_at,
    status: run.status,
    steps: run.steps.map((step) => ({
      displayName: step.display_name,
      durationSeconds: step.duration_seconds,
      error: step.error
        ? { code: step.error.code, message: step.error.message }
        : null,
      implementationId: step.implementation_id,
      metrics: step.metrics,
      status: step.status,
      stepId: step.step_id,
      stepType: step.step_type,
    })),
    updatedAt: run.updated_at,
  };
}
function mapOcrPipelineRunOcrResult(
  result: OcrPipelineRunOcrResultDto,
): OcrPipelineRunOcrResult {
  return {
    averageConfidence: result.average_confidence,
    failedPageCount: result.failed_page_count,
    lowConfidencePageCount: result.low_confidence_page_count,
    modelId: result.model_id,
    pages: result.pages.map(mapOcrPipelineRunOcrPageResult),
    pagesTruncated: result.pages_truncated,
    providerId: result.provider_id,
    status: result.status,
    succeededPageCount: result.succeeded_page_count,
    totalPageCount: result.total_page_count,
    warningCount: result.warning_count,
  };
}

function mapOcrPipelineRunOcrPageResult(
  page: OcrPipelineRunOcrPageResultDto,
): OcrPipelineRunOcrPageResult {
  return {
    confidence: page.confidence,
    errorCode: page.error_code,
    fallbackReasonCodes: page.fallback_reason_codes,
    fallbackUsed: page.fallback_used,
    lines: page.lines,
    linesTruncated: page.lines_truncated,
    pageNumber: page.page_number,
    primaryErrorCode: page.primary_error_code,
    status: page.status,
    text: page.text,
    textTruncated: page.text_truncated,
    warningCodes: page.warning_codes,
  };
}
