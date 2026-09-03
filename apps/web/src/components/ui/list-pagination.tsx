"use client";

import { Button } from "@/components/ui/button";

import { getListPaginationRange } from "./list-pagination-range";

interface ListPaginationMeta {
  hasMore: boolean;
  limit: number;
  offset: number;
  returnedCount: number;
  total: number;
}

export interface ListPaginationProps {
  isPending: boolean;
  meta: ListPaginationMeta | undefined;
  nextLabel: string;
  onOffsetChange: (offset: number) => void;
  previousLabel: string;
  summary: (range: { first: number; last: number; total: number }) => string;
}

export function ListPagination({
  isPending,
  meta,
  nextLabel,
  onOffsetChange,
  previousLabel,
  summary,
}: ListPaginationProps) {
  if (!meta || meta.total === 0) return null;

  const range = getListPaginationRange(meta);

  return (
    <div className="flex items-center justify-between gap-3 px-1 pb-1">
      <p className="text-sm text-muted-foreground">{summary(range)}</p>
      <div className="flex gap-2">
        <Button
          disabled={meta.offset === 0 || isPending}
          onClick={() => onOffsetChange(Math.max(0, meta.offset - meta.limit))}
          size="sm"
          type="button"
          variant="outline"
        >
          {previousLabel}
        </Button>
        <Button
          disabled={!meta.hasMore || isPending}
          onClick={() => onOffsetChange(meta.offset + meta.limit)}
          size="sm"
          type="button"
          variant="outline"
        >
          {nextLabel}
        </Button>
      </div>
    </div>
  );
}
