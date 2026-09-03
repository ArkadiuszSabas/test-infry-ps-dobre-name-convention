import { keepPreviousData, queryOptions } from "@tanstack/react-query";

import { buildListQueryKey } from "./list-contract";

interface ListQueryOptionsInput<Query extends object, Page> {
  enabled?: boolean;
  query: Query;
  queryKey: readonly unknown[];
  request: (query: Query, signal: AbortSignal) => Promise<Page>;
}

export function listQueryOptions<Query extends object, Page>({
  enabled = true,
  query,
  queryKey,
  request,
}: ListQueryOptionsInput<Query, Page>) {
  return queryOptions({
    enabled,
    placeholderData: keepPreviousData,
    queryFn: ({ signal }) => request(query, signal),
    queryKey: buildListQueryKey(queryKey, query),
    retry: false,
  });
}
