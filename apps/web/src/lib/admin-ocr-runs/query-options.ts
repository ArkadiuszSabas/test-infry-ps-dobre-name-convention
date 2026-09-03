import { queryOptions } from "@tanstack/react-query";

import { adminOcrRunsClient } from "./api";
import type { AdminOcrRunListFilters } from "./types";

export const adminOcrRunQueryKeys = {
  all: ["admin", "ocr-runs"] as const,
  lists: () => [...adminOcrRunQueryKeys.all, "list"] as const,
  list: (filters: AdminOcrRunListFilters) =>
    [...adminOcrRunQueryKeys.lists(), filters] as const,
  details: () => [...adminOcrRunQueryKeys.all, "detail"] as const,
  detail: (runId: string | null) =>
    [...adminOcrRunQueryKeys.details(), runId] as const,
  pipelines: () => [...adminOcrRunQueryKeys.all, "pipelines"] as const,
};

export function adminOcrRunListQueryOptions(filters: AdminOcrRunListFilters) {
  return queryOptions({
    queryKey: adminOcrRunQueryKeys.list(filters),
    queryFn: ({ signal }) => adminOcrRunsClient.list(filters, { signal }),
    refetchInterval: filters.view === "active" ? 5_000 : false,
    refetchIntervalInBackground: false,
    retry: false,
  });
}

export function publishedOcrPipelineQueryOptions() {
  return queryOptions({
    queryKey: adminOcrRunQueryKeys.pipelines(),
    queryFn: ({ signal }) =>
      adminOcrRunsClient.listPublishedPipelines({ signal }),
    staleTime: 60_000,
    retry: false,
  });
}

export function adminOcrRunDetailQueryOptions(runId: string | null) {
  return queryOptions({
    enabled: Boolean(runId),
    queryKey: adminOcrRunQueryKeys.detail(runId),
    queryFn: ({ signal }) => {
      if (!runId) {
        throw new Error("OCR run id is required.");
      }
      return adminOcrRunsClient.detail(runId, { signal });
    },
    retry: false,
  });
}
