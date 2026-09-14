"use client";

import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";

interface AdminOcrRunsPaginationProps {
  canGoNext: boolean;
  canGoPrevious: boolean;
  isFetching: boolean;
  onGoNext: () => void;
  onGoPrevious: () => void;
  returnedCount: number;
  offset: number;
  total: number;
}

export function AdminOcrRunsPagination({
  canGoNext,
  canGoPrevious,
  isFetching,
  onGoNext,
  onGoPrevious,
  offset,
  returnedCount,
  total,
}: AdminOcrRunsPaginationProps) {
  const t = useTranslations("AdminOcrRuns");

  return (
    <div className="flex items-center justify-between gap-3">
      <p className="text-sm text-muted-foreground">
        {t("pageSummary", {
          from: returnedCount ? offset + 1 : 0,
          to: returnedCount ? offset + returnedCount : 0,
          total,
        })}
      </p>
      <div className="flex gap-2">
        <Button
          disabled={!canGoPrevious || isFetching}
          onClick={onGoPrevious}
          size="sm"
          type="button"
          variant="outline"
        >
          {t("previous")}
        </Button>
        <Button
          disabled={!canGoNext || isFetching}
          onClick={onGoNext}
          size="sm"
          type="button"
          variant="outline"
        >
          {t("next")}
        </Button>
      </div>
    </div>
  );
}
