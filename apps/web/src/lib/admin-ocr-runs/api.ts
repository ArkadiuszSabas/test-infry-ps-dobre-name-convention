import { apiFetch } from "@/lib/api/client";

import type {
  AdminOcrRunDetailEnvelope,
  AdminOcrRunListEnvelope,
  AdminOcrRunListFilters,
  OcrRunStatus,
  PublishedOcrPipelineListEnvelope,
  PublishedOcrPipelineOption,
} from "./types";

interface RequestOptions {
  signal?: AbortSignal;
  csrfToken?: string;
}

export const adminOcrRunsClient = {
  list(
    filters: AdminOcrRunListFilters,
    options: RequestOptions = {},
  ): Promise<AdminOcrRunListEnvelope> {
    return apiFetch(`/admin/ocr/pipeline-runs?${buildListParams(filters)}`, {
      method: "GET",
      signal: options.signal,
    });
  },

  detail(
    runId: string,
    options: RequestOptions = {},
  ): Promise<AdminOcrRunDetailEnvelope> {
    return apiFetch(`/admin/ocr/pipeline-runs/${encodeURIComponent(runId)}`, {
      method: "GET",
      signal: options.signal,
    });
  },

  async cancel(
    runId: string,
    options: RequestOptions = {},
  ): Promise<OcrRunStatus> {
    const envelope = await apiFetch<{ data: { status: OcrRunStatus } }>(
      `/ocr/pipeline-runs/${encodeURIComponent(runId)}/cancel`,
      {
        csrfToken: options.csrfToken,
        method: "POST",
        signal: options.signal,
      },
    );
    return envelope.data.status;
  },

  async start(
    documentId: string,
    pipelineId: string,
    options: RequestOptions = {},
  ): Promise<string> {
    const envelope = await apiFetch<{ data: { id: string } }>(
      `/documents/${encodeURIComponent(documentId)}/ocr/pipeline-runs`,
      {
        csrfToken: options.csrfToken,
        json: { pipeline_id: pipelineId },
        method: "POST",
        signal: options.signal,
      },
    );
    return envelope.data.id;
  },

  async listPublishedPipelines(
    options: RequestOptions = {},
  ): Promise<PublishedOcrPipelineOption[]> {
    const envelope = await apiFetch<PublishedOcrPipelineListEnvelope>(
      "/ocr/pipelines",
      { method: "GET", signal: options.signal },
    );
    return envelope.data.pipelines.map((pipeline) => ({
      id: pipeline.id,
      isDefault: pipeline.is_default,
      name: pipeline.name,
      publishedVersion: pipeline.published_version,
    }));
  },
};

export function buildListParams(filters: AdminOcrRunListFilters): string {
  const params = new URLSearchParams({
    limit: String(filters.limit),
    offset: String(filters.offset),
    view: filters.view,
  });
  append(params, "status", filters.status);
  append(params, "pipeline_id", filters.pipelineId);
  append(params, "document_type_id", filters.documentTypeId);
  append(params, "source", filters.source);
  append(params, "connector", filters.connector);
  append(params, "created_from", filters.createdFrom);
  append(params, "created_to", filters.createdTo);
  if (filters.staleMs) {
    params.set(
      "updated_before",
      new Date(Date.now() - filters.staleMs).toISOString(),
    );
  }
  append(params, "search", filters.search);
  return params.toString();
}

function append(params: URLSearchParams, key: string, value?: string) {
  if (value) {
    params.set(key, value);
  }
}
