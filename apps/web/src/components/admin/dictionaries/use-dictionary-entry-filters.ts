"use client";

import { useState } from "react";

import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { DictionaryStatusFilter } from "@/lib/admin-settings/types";

import {
  isDictionaryStatusFilter,
  normalizeDictionaryEntrySearch,
} from "./dictionary-entry-filter-counts";

export function useDictionaryEntryFilters() {
  const [status, setStatus] = useState<DictionaryStatusFilter>("active");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
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

  return {
    handleSearchChange,
    handleStatusChange,
    normalizedSearch,
    offset,
    search,
    setOffset,
    status,
  };
}
