import type { QueryClient } from "@tanstack/react-query";

export function clearBrowserSessionQueryCache(queryClient: QueryClient) {
  queryClient.removeQueries();
}
