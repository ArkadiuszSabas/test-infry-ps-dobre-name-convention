"use client";

import { useTranslations } from "next-intl";

import { runStatusClassName } from "@/components/inbox/ocr-pipeline-run-status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { getOcrPipelineRunLabel } from "@/lib/inbox/ocr-pipeline-run-label";
import type { OcrPipelineRun } from "@/lib/inbox/types";

export interface RunHistoryListProps {
  activeRunId: string;
  formatDate: (value: string) => string;
  onSelectRun: (runId: string) => void;
  runs: readonly OcrPipelineRun[];
}

export function RunHistoryList({
  activeRunId,
  formatDate,
  onSelectRun,
  runs,
}: RunHistoryListProps) {
  const t = useTranslations("Inbox.ocrRun");

  return (
    <div className="space-y-2">
      <Separator />
      <h3 className="text-sm font-medium text-foreground">
        {t("history.title")}
      </h3>
      <ul className="space-y-1">
        {runs.map((run) => {
          const pipelineLabel = getOcrPipelineRunLabel(run);
          return (
            <li key={run.id}>
              <Button
                aria-pressed={activeRunId === run.id}
                className="h-auto w-full justify-start gap-2 px-2 py-1.5 text-left"
                onClick={() => onSelectRun(run.id)}
                size="sm"
                type="button"
                variant={activeRunId === run.id ? "secondary" : "ghost"}
              >
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate">{formatDate(run.createdAt)}</span>
                  <span className="truncate text-xs font-normal opacity-75">
                    {t(pipelineLabel.key, pipelineLabel.values)}
                  </span>
                </span>
                <Badge
                  className={runStatusClassName(run.status)}
                  variant="outline"
                >
                  {t(`status.${run.status}`)}
                </Badge>
              </Button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
