import { queryOptions } from "@tanstack/react-query";

import { approvalSettingsClient } from "@/lib/approval-settings/api";

export const approvalSettingsQueryKeys = {
  all: ["document-approval-settings"] as const,
  settings: () => [...approvalSettingsQueryKeys.all, "settings"] as const,
};

export function approvalSettingsQueryOptions() {
  return queryOptions({
    queryKey: approvalSettingsQueryKeys.settings(),
    queryFn: ({ signal }) => approvalSettingsClient.getSettings({ signal }),
    retry: false,
    staleTime: 60_000,
  });
}
