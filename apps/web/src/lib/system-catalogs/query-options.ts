import { queryOptions } from "@tanstack/react-query";

import { systemCatalogClient } from "./api";
import type { SystemCatalogKey } from "./types";

export const systemCatalogQueryKeys = {
  all: ["system-catalogs"] as const,
  definition: (systemCatalogKey: SystemCatalogKey) =>
    [...systemCatalogQueryKeys.all, systemCatalogKey, "definition"] as const,
  options: (systemCatalogKey: SystemCatalogKey) =>
    [...systemCatalogQueryKeys.all, systemCatalogKey, "options"] as const,
};

export function systemCatalogDefinitionQueryOptions(
  systemCatalogKey: SystemCatalogKey,
  enabled = true,
) {
  return queryOptions({
    enabled,
    queryKey: systemCatalogQueryKeys.definition(systemCatalogKey),
    queryFn: ({ signal }) =>
      systemCatalogClient.getSystemCatalogDefinition(systemCatalogKey, {
        signal,
      }),
    retry: false,
  });
}

export function systemCatalogOptionsQueryOptions(
  systemCatalogKey: SystemCatalogKey,
  enabled = true,
) {
  return queryOptions({
    enabled,
    queryKey: systemCatalogQueryKeys.options(systemCatalogKey),
    queryFn: ({ signal }) =>
      systemCatalogClient.listSystemCatalogOptions(systemCatalogKey, {
        signal,
      }),
    retry: false,
  });
}
