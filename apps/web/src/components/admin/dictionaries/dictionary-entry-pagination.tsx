"use client";

import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { DICTIONARY_ENTRY_PAGE_SIZE } from "@/lib/admin-settings/query-options";

interface DictionaryEntryPaginationProps {
  hasMore: boolean;
  isPending: boolean;
  offset: number;
  returnedCount: number;
  setOffset: (updater: (current: number) => number) => void;
  totalCount: number;
}

export function DictionaryEntryPagination({
  hasMore,
  isPending,
  offset,
  returnedCount,
  setOffset,
  totalCount,
}: DictionaryEntryPaginationProps) {
  const t = useTranslations("AdminSettings.customDictionaryDetail");

  return (
    <div className="flex items-center justify-between gap-3">
      <p className="text-sm text-muted-foreground">
        {t("entries.pageSummary", {
          count: returnedCount,
          total: totalCount,
        })}
      </p>
      <div className="flex gap-2">
        <Button
          disabled={offset === 0 || isPending}
          onClick={() =>
            setOffset((current) =>
              Math.max(0, current - DICTIONARY_ENTRY_PAGE_SIZE),
            )
          }
          size="sm"
          type="button"
          variant="outline"
        >
          {t("entries.previous")}
        </Button>
        <Button
          disabled={!hasMore || isPending}
          onClick={() =>
            setOffset((current) => current + DICTIONARY_ENTRY_PAGE_SIZE)
          }
          size="sm"
          type="button"
          variant="outline"
        >
          {t("entries.next")}
        </Button>
      </div>
    </div>
  );
}
