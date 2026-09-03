"use client";

import { useTranslations } from "next-intl";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PublishedOcrPipelineOption } from "@/lib/inbox/types";

export interface OcrPipelineSelectorProps {
  disabled: boolean;
  loading: boolean;
  onValueChange: (pipelineId: string) => void;
  pipelines: readonly PublishedOcrPipelineOption[];
  value: string | null;
}

export function OcrPipelineSelector({
  disabled,
  loading,
  onValueChange,
  pipelines,
  value,
}: OcrPipelineSelectorProps) {
  const t = useTranslations("Inbox.ocrRun.pipelineSelector");

  return (
    <Select
      disabled={disabled}
      onValueChange={onValueChange}
      value={value ?? ""}
    >
      <SelectTrigger
        aria-label={t("label")}
        className="min-w-48 max-w-64"
        size="sm"
      >
        <SelectValue placeholder={loading ? t("loading") : t("placeholder")} />
      </SelectTrigger>
      <SelectContent align="end">
        {pipelines.map((pipeline) => (
          <SelectItem
            key={pipeline.id}
            textValue={pipeline.name}
            value={pipeline.id}
          >
            <span className="flex min-w-0 items-center gap-2">
              <span className="truncate">{pipeline.name}</span>
              {pipeline.isDefault ? (
                <span className="text-xs text-muted-foreground">
                  {t("default")}
                </span>
              ) : null}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
