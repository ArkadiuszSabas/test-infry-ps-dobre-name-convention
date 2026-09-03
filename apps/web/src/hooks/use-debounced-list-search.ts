"use client";

import { LIST_SEARCH_DEBOUNCE_MS } from "@/lib/api/list-contract";

import { useDebouncedValue } from "./use-debounced-value";

export function useDebouncedListSearch(value: string): string {
  return useDebouncedValue(value, LIST_SEARCH_DEBOUNCE_MS);
}
