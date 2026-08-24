import { queryOptions } from "@tanstack/react-query";

import { ocrPipelinesClient } from "./api";

export const ocrPipelineQueryKeys = {
  all: ["admin", "ocr-pipelines"] as const,
  blockCatalog: () => [...ocrPipelineQueryKeys.all, "block-catalog"] as const,
  details: () => [...ocrPipelineQueryKeys.pipelines(), "detail"] as const,
  detail: (pipelineId: string | null) =>
    [...ocrPipelineQueryKeys.details(), pipelineId] as const,
  pipelines: () => [...ocrPipelineQueryKeys.all, "pipelines"] as const,
};

export function ocrPipelineBlockCatalogQueryOptions() {
  return queryOptions({
    queryKey: ocrPipelineQueryKeys.blockCatalog(),
    queryFn: ({ signal }) => ocrPipelinesClient.listBlockCatalog({ signal }),
    retry: false,
  });
}

export function ocrPipelinesListQueryOptions() {
  return queryOptions({
    queryKey: ocrPipelineQueryKeys.pipelines(),
    queryFn: ({ signal }) => ocrPipelinesClient.listPipelines({ signal }),
    retry: false,
  });
}

export function ocrPipelineDetailQueryOptions(pipelineId: string | null) {
  return queryOptions({
    enabled: Boolean(pipelineId),
    queryKey: ocrPipelineQueryKeys.detail(pipelineId),
    queryFn: ({ signal }) => {
      if (!pipelineId) {
        throw new Error("OCR pipeline id is required.");
      }

      return ocrPipelinesClient.getPipeline(pipelineId, { signal });
    },
    retry: false,
  });
}
