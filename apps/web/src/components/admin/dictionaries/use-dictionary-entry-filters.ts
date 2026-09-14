"use client";

import { useState } from "react";

import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { DictionaryStatusFilter } from "@/lib/admin-settings/types";
import type { DictionaryEntrySortField } from "@/lib/admin-settings/dictionary-api";
import type { SortState } from "@/lib/collection-view";

import {
  isDictionaryStatusFilter,
  normalizeDictionaryEntrySearch,
} from "./dictionary-entry-filter-counts";

export function useDictionaryEntryFilters() {
  const [status, setStatus] = useState<DictionaryStatusFilter>("active");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [sort, setSort] = useState<SortState<DictionaryEntrySortField>>({
    column: "sort_order",
    direction: "asc",
  });
  const debouncedSearch = useDebouncedValue(search, 250);
  const normalizedSearch = normalizeDictionaryEntrySearch(debouncedSearch);

  function handleStatusChange(value: string) {
    if (isDictionaryStatusFilter(value)) {
      setOffset(0);
      setStatus(value);
    }
  }

  function handleSearchChange(value: string) {
    setOffset(0);
    setSearch(value);
  }

  function handleSortChange(value: SortState<DictionaryEntrySortField>) {
    setOffset(0);
    setSort(value);
  }

  return {
    handleSearchChange,
    handleSortChange,
    handleStatusChange,
    normalizedSearch,
    offset,
    search,
    setOffset,
    sort,
    status,
  };
}
