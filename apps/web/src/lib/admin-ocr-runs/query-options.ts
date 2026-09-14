import { queryOptions } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { listQueryOptions } from "@/lib/api/list-query-options";

import { adminOcrRunsClient } from "./api";
import type {
  AdminOcrRunListEnvelope,
  AdminOcrRunListFilters,
  AdminOcrRunView,
} from "./types";

export const ADMIN_OCR_RUN_ACTIVE_REFETCH_INTERVAL_MS = 1_000;

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
  const listOptions = listQueryOptions({
    query: filters,
    queryKey: adminOcrRunQueryKeys.lists(),
    request: (query, signal) => adminOcrRunsClient.list(query, { signal }),
  });
  return queryOptions({
    ...listOptions,
    placeholderData: (previousData, previousQuery) =>
      keepPreviousAdminOcrRunPageForView(
        filters.view,
        previousData,
        previousQuery?.queryKey,
      ),
    refetchInterval: (query) =>
      getAdminOcrRunListRefetchInterval(filters.view, query.state.data),
    refetchIntervalInBackground: false,
    retry: false,
  });
}

export function getAdminOcrRunListRefetchInterval(
  view: AdminOcrRunView,
  page: AdminOcrRunListEnvelope | undefined,
): number | false {
  if (view === "active") {
    return ADMIN_OCR_RUN_ACTIVE_REFETCH_INTERVAL_MS;
  }
  return page?.data.runs.some((run) => run.status === "cancelling")
    ? ADMIN_OCR_RUN_ACTIVE_REFETCH_INTERVAL_MS
    : false;
}

export function keepPreviousAdminOcrRunPageForView<Page>(
  view: AdminOcrRunView,
  previousData: Page | undefined,
  previousQueryKey: readonly unknown[] | undefined,
): Page | undefined {
  const previousFilters = previousQueryKey?.at(-1);
  if (
    !previousFilters ||
    typeof previousFilters !== "object" ||
    !("view" in previousFilters)
  ) {
    return undefined;
  }
  return previousFilters.view === view ? previousData : undefined;
}

export function invalidateAdminOcrRunLists(
  queryClient: QueryClient,
): Promise<void> {
  return queryClient.invalidateQueries({
    queryKey: adminOcrRunQueryKeys.lists(),
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
