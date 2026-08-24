"use client";

import { useQueries } from "@tanstack/react-query";

import { dictionaryEntriesQueryOptions } from "@/lib/admin-settings/query-options";
import type { DictionaryStatusFilter } from "@/lib/admin-settings/types";
import { catalogStatusFilters } from "@/lib/admin-settings/view-model";

interface UseDictionaryEntryFilterCountsInput {
  activeTotalCount: number | undefined;
  dictionaryId: string;
  search: string | null;
  status: DictionaryStatusFilter;
}

export function useDictionaryEntryFilterCounts({
  activeTotalCount,
  dictionaryId,
  search,
  status,
}: UseDictionaryEntryFilterCountsInput) {
  const entryCountQueries = useQueries({
    queries: catalogStatusFilters.map((filter) =>
      dictionaryEntriesQueryOptions({
        dictionaryId,
        offset: 0,
        search,
        status: filter,
      }),
    ),
  });

  return (filter: DictionaryStatusFilter) => {
    const queryIndex = catalogStatusFilters.findIndex(
      (candidate) => candidate === filter,
    );

    return (
      entryCountQueries[queryIndex]?.data?.meta.totalCount ??
      (filter === status ? activeTotalCount : undefined) ??
      0
    );
  };
}

export function isDictionaryStatusFilter(
  value: string,
): value is DictionaryStatusFilter {
  return catalogStatusFilters.some((filter) => filter === value);
}

export function normalizeDictionaryEntrySearch(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}
