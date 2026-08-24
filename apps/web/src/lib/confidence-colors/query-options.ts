import { queryOptions } from "@tanstack/react-query";

import { confidenceColorsClient } from "@/lib/confidence-colors/api";

export const confidenceColorQueryKeys = {
  all: ["ocr-confidence-colors"] as const,
  settings: () => [...confidenceColorQueryKeys.all, "settings"] as const,
};

export function adminConfidenceColorSettingsQueryOptions() {
  return queryOptions({
    queryKey: confidenceColorQueryKeys.settings(),
    queryFn: ({ signal }) =>
      confidenceColorsClient.getAdminSettings({ signal }),
    retry: false,
    staleTime: 60_000,
  });
}

export function reviewConfidenceColorSettingsQueryOptions() {
  return queryOptions({
    queryKey: confidenceColorQueryKeys.settings(),
    queryFn: ({ signal }) =>
      confidenceColorsClient.getReviewSettings({ signal }),
    retry: false,
    staleTime: 60_000,
  });
}
