"use client";

import { PlayIcon, XIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PublishedOcrPipelineOption } from "@/lib/admin-ocr-runs/types";

interface AdminOcrRunsBulkActionsProps {
  isQueueing: boolean;
  onClearSelection: () => void;
  onPipelineChange: (pipelineId: string) => void;
  onQueueSelected: () => void;
  pipelines: readonly PublishedOcrPipelineOption[];
  pipelinesLoading: boolean;
  selectedCount: number;
  selectedPipelineId: string | null;
}

export function AdminOcrRunsBulkActions({
  isQueueing,
  onClearSelection,
  onPipelineChange,
  onQueueSelected,
  pipelines,
  pipelinesLoading,
  selectedCount,
  selectedPipelineId,
}: AdminOcrRunsBulkActionsProps) {
  const t = useTranslations("AdminOcrRuns");

  return (
    <>
      <span className="px-2 text-sm font-medium">
        {t("bulk.selected", { count: selectedCount })}
      </span>
      <Select
        disabled={pipelinesLoading || pipelines.length === 0}
        onValueChange={onPipelineChange}
        value={selectedPipelineId ?? ""}
      >
        <SelectTrigger
          aria-label={t("bulk.pipeline")}
          className="min-w-48 border-0 shadow-none"
          size="sm"
        >
          <SelectValue
            placeholder={
              pipelinesLoading ? t("bulk.loadingPipelines") : t("bulk.pipeline")
            }
          />
        </SelectTrigger>
        <SelectContent>
          {pipelines.map((pipeline) => (
            <SelectItem key={pipeline.id} value={pipeline.id}>
              {pipeline.name} · v{pipeline.publishedVersion}
              {pipeline.isDefault ? ` · ${t("bulk.defaultPipeline")}` : ""}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button
        disabled={!selectedPipelineId || isQueueing}
        onClick={onQueueSelected}
        size="sm"
      >
        <PlayIcon />
        {isQueueing ? t("bulk.queueing") : t("bulk.queue")}
      </Button>
      <IconTooltipButton
        aria-label={t("bulk.clearSelection")}
        onClick={onClearSelection}
        tooltip={t("bulk.clearSelection")}
        variant="ghost"
      >
        <XIcon />
      </IconTooltipButton>
    </>
  );
}
