"use client";

import {
  ArchiveIcon,
  CheckCircle2Icon,
  CircleAlertIcon,
  CopyIcon,
  Clock3Icon,
  PencilIcon,
  StarIcon,
  Trash2Icon,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import {
  DataListRow,
  DataListSkeletonRows,
  DataListTable,
} from "@/components/ui/data-list";
import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import {
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TruncatedTableText,
} from "@/components/ui/table";
import type { OcrPipelineSummary } from "@/lib/ocr-pipelines/types";
import {
  canEditOcrPipelineSummary,
  pipelineHasUnpublishedDraftChanges,
  validationState,
} from "@/lib/ocr-pipelines/view-model";
import { cn } from "@/lib/utils";

export type OcrPipelineActionKind =
  | "archive"
  | "delete"
  | "duplicate"
  | "edit"
  | "makeDefault"
  | "open";

interface PipelineListProps {
  isLoading: boolean;
  onAction: (
    action: OcrPipelineActionKind,
    pipeline: OcrPipelineSummary,
  ) => void;
  pipelines: OcrPipelineSummary[];
  selectedPipelineId: string | null;
}

const lifecycleIcons = {
  archived: ArchiveIcon,
  draft: PencilIcon,
  published: CheckCircle2Icon,
} as const;

const validationIcons = {
  invalid: CircleAlertIcon,
  unknown: Clock3Icon,
  valid: CheckCircle2Icon,
} as const;

export function PipelineList({
  isLoading,
  onAction,
  pipelines,
  selectedPipelineId,
}: PipelineListProps) {
  const t = useTranslations("AdminOcrPipelines");
  const lifecycle = useTranslations("AdminOcrPipelines.lifecycle");
  const validation = useTranslations("AdminOcrPipelines.validationState");

  return (
    <div className="@container/pipeline-list">
      <DataListTable>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[36%] @max-[48rem]/pipeline-list:w-[52%]">
              {t("columns.pipeline")}
            </TableHead>
            <TableHead className="w-28 @max-[48rem]/pipeline-list:hidden">
              {t("columns.lifecycle")}
            </TableHead>
            <TableHead className="w-28 @max-[48rem]/pipeline-list:hidden">
              {t("columns.validation")}
            </TableHead>
            <TableHead className="w-28">{t("columns.updatedAt")}</TableHead>
            <TableHead className="w-52 @max-[48rem]/pipeline-list:w-44 text-right">
              {t("columns.actions")}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? <DataListSkeletonRows columns={5} /> : null}
          {!isLoading && pipelines.length === 0 ? (
            <DataListRow>
              <TableCell colSpan={5}>
                <div className="py-8 text-center text-sm text-muted-foreground">
                  {t("emptyDescription")}
                </div>
              </TableCell>
            </DataListRow>
          ) : null}
          {!isLoading
            ? pipelines.map((pipeline) => (
                <DataListRow
                  className={cn(
                    selectedPipelineId === pipeline.id &&
                      "bg-accent/70 [&>td]:border-primary/40",
                  )}
                  key={pipeline.id}
                >
                  <TableCell className="w-[36%] @max-[48rem]/pipeline-list:w-[52%]">
                    <div className="flex min-w-0 flex-col gap-1">
                      <div className="flex min-w-0 items-center gap-2">
                        <button
                          aria-current={
                            selectedPipelineId === pipeline.id
                              ? "true"
                              : undefined
                          }
                          className={cn(
                            "min-w-0 appearance-none rounded-sm border-0 bg-transparent p-0 text-left font-medium text-foreground underline-offset-4 hover:underline",
                            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                          )}
                          onClick={() => onAction("open", pipeline)}
                          type="button"
                        >
                          <TruncatedTableText value={pipeline.name} />
                        </button>
                        {pipeline.isDefault ? (
                          <Badge
                            className="@max-[48rem]/pipeline-list:hidden"
                            title={t("badges.default")}
                          >
                            <StarIcon data-icon="inline-start" />
                            <span className="@max-[48rem]/pipeline-list:hidden">
                              {t("badges.default")}
                            </span>
                          </Badge>
                        ) : null}
                        {pipelineHasUnpublishedDraftChanges(pipeline) ? (
                          <Badge
                            className="@max-[48rem]/pipeline-list:hidden"
                            title={t("badges.draftChanges")}
                            variant="secondary"
                          >
                            <Clock3Icon data-icon="inline-start" />
                            <span className="@max-[48rem]/pipeline-list:hidden">
                              {t("badges.draftChanges")}
                            </span>
                          </Badge>
                        ) : null}
                      </div>
                      <div className="hidden flex-wrap gap-x-2 text-xs text-muted-foreground @max-[48rem]/pipeline-list:flex">
                        {pipeline.isDefault ? (
                          <span>{t("badges.default")}</span>
                        ) : null}
                        {pipelineHasUnpublishedDraftChanges(pipeline) ? (
                          <span>{t("badges.draftChanges")}</span>
                        ) : null}
                        <span>{lifecycle(pipeline.lifecycle)}</span>
                        <span>
                          {validation(
                            validationState(pipeline.lastValidationValid),
                          )}
                        </span>
                      </div>
                      {pipeline.description ? (
                        <TruncatedTableText
                          className="text-xs text-muted-foreground"
                          value={pipeline.description}
                        />
                      ) : null}
                    </div>
                  </TableCell>
                  <TableCell className="w-28 @max-[48rem]/pipeline-list:hidden">
                    <LifecycleBadge lifecycle={pipeline.lifecycle} />
                  </TableCell>
                  <TableCell className="w-28 @max-[48rem]/pipeline-list:hidden">
                    <ValidationBadge valid={pipeline.lastValidationValid} />
                  </TableCell>
                  <TableCell className="w-28">
                    <span className="text-xs text-muted-foreground">
                      {formatDate(pipeline.updatedAt)}
                    </span>
                  </TableCell>
                  <TableCell className="w-52 @max-[48rem]/pipeline-list:w-44">
                    <div className="flex justify-end gap-1.5">
                      <IconTooltipButton
                        aria-label={t("actions.edit", { name: pipeline.name })}
                        disabled={!canEditOcrPipelineSummary(pipeline)}
                        onClick={() => onAction("edit", pipeline)}
                        tooltip={t("tooltips.edit")}
                        type="button"
                        variant="ghost"
                      >
                        <PencilIcon />
                      </IconTooltipButton>
                      <IconTooltipButton
                        aria-label={t("actions.duplicate", {
                          name: pipeline.name,
                        })}
                        disabled={pipeline.lifecycle === "archived"}
                        onClick={() => onAction("duplicate", pipeline)}
                        tooltip={t("tooltips.duplicate")}
                        type="button"
                        variant="ghost"
                      >
                        <CopyIcon />
                      </IconTooltipButton>
                      <IconTooltipButton
                        aria-label={t("actions.makeDefault", {
                          name: pipeline.name,
                        })}
                        disabled={
                          pipeline.lifecycle !== "published" ||
                          pipeline.isDefault
                        }
                        onClick={() => onAction("makeDefault", pipeline)}
                        tooltip={t("tooltips.makeDefault")}
                        type="button"
                        variant="ghost"
                      >
                        <StarIcon />
                      </IconTooltipButton>
                      <IconTooltipButton
                        aria-label={t("actions.archive", {
                          name: pipeline.name,
                        })}
                        disabled={pipeline.lifecycle !== "published"}
                        onClick={() => onAction("archive", pipeline)}
                        tooltip={t("tooltips.archive")}
                        type="button"
                        variant="ghost"
                      >
                        <ArchiveIcon />
                      </IconTooltipButton>
                      <IconTooltipButton
                        aria-label={t("actions.delete", {
                          name: pipeline.name,
                        })}
                        disabled={pipeline.lifecycle !== "draft"}
                        onClick={() => onAction("delete", pipeline)}
                        tooltip={t("tooltips.delete")}
                        type="button"
                        variant="ghost"
                      >
                        <Trash2Icon />
                      </IconTooltipButton>
                    </div>
                  </TableCell>
                </DataListRow>
              ))
            : null}
        </TableBody>
      </DataListTable>
    </div>
  );
}

function LifecycleBadge({
  lifecycle,
}: {
  lifecycle: OcrPipelineSummary["lifecycle"];
}) {
  const t = useTranslations("AdminOcrPipelines.lifecycle");
  const Icon = lifecycleIcons[lifecycle];

  return (
    <Badge title={t(lifecycle)} variant="outline">
      <Icon data-icon="inline-start" />
      <span className="@max-[48rem]/pipeline-list:hidden">{t(lifecycle)}</span>
    </Badge>
  );
}

function ValidationBadge({ valid }: { valid: boolean | null }) {
  const t = useTranslations("AdminOcrPipelines.validationState");
  const state = validationState(valid);
  const Icon = validationIcons[state];

  return (
    <Badge
      title={t(state)}
      variant={state === "invalid" ? "destructive" : "outline"}
    >
      <Icon data-icon="inline-start" />
      <span className="@max-[48rem]/pipeline-list:hidden">{t(state)}</span>
    </Badge>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
