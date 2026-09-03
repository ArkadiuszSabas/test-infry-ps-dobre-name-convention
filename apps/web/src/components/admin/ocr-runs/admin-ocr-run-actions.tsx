"use client";

import {
  ActivityIcon,
  EyeIcon,
  MoreHorizontalIcon,
  RefreshCwIcon,
  SquareArrowOutUpRightIcon,
  WorkflowIcon,
  XCircleIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import { Link } from "@/i18n/navigation";
import { buildLangfuseSessionUrl } from "@/lib/admin-ocr-runs/langfuse";
import type {
  AdminOcrRunSummaryDto,
  PublishedOcrPipelineOption,
} from "@/lib/admin-ocr-runs/types";
import { canCancelRun, canRerunRun } from "@/lib/admin-ocr-runs/view-model";

interface AdminOcrRunActionsProps {
  langfuseProjectUrl: string | null;
  onCancel: (run: AdminOcrRunSummaryDto) => void;
  onRerun: (run: AdminOcrRunSummaryDto, pipelineId: string) => void;
  onSelect: (runId: string) => void;
  pending: boolean;
  pipelines: readonly PublishedOcrPipelineOption[];
  pipelinesLoading: boolean;
  run: AdminOcrRunSummaryDto;
}

export function AdminOcrRunActions({
  langfuseProjectUrl,
  onCancel,
  onRerun,
  onSelect,
  pending,
  pipelines,
  pipelinesLoading,
  run,
}: AdminOcrRunActionsProps) {
  const t = useTranslations("AdminOcrRuns");
  const rerunnable = canRerunRun(run);
  const langfuseUrl = langfuseProjectUrl
    ? buildLangfuseSessionUrl(langfuseProjectUrl, run.id)
    : null;

  return (
    <div className="flex shrink-0 justify-end gap-1 whitespace-nowrap">
      <IconTooltipButton
        aria-label={t("actions.detailsFor", { name: run.document_name })}
        onClick={() => onSelect(run.id)}
        tooltip={t("actions.details")}
        variant="secondary"
      >
        <EyeIcon />
      </IconTooltipButton>
      <IconTooltipButton
        asChild
        tooltip={t("actions.openDocumentShort")}
        variant="secondary"
      >
        <Link
          aria-label={t("actions.openDocument", { name: run.document_name })}
          href={`/documents/${run.document_id}`}
        >
          <SquareArrowOutUpRightIcon />
        </Link>
      </IconTooltipButton>
      {langfuseUrl ? (
        <IconTooltipButton
          asChild
          tooltip={t("actions.openLangfuseShort")}
          variant="secondary"
        >
          <a
            aria-label={t("actions.openLangfuse", {
              name: run.document_name,
            })}
            href={langfuseUrl}
            rel="noopener noreferrer"
            target="_blank"
          >
            <ActivityIcon />
          </a>
        </IconTooltipButton>
      ) : (
        <IconTooltipButton
          aria-label={t("actions.langfuseUnavailable")}
          disabled
          tooltip={t("actions.langfuseUnavailable")}
          variant="secondary"
        >
          <ActivityIcon />
        </IconTooltipButton>
      )}
      <IconTooltipButton
        aria-label={t("actions.rerunLast", { name: run.document_name })}
        disabled={!rerunnable || pending}
        onClick={() => onRerun(run, run.pipeline_id)}
        tooltip={t("actions.rerunLastShort")}
        variant="secondary"
      >
        <RefreshCwIcon className={pending ? "animate-spin" : undefined} />
      </IconTooltipButton>
      <IconTooltipButton
        aria-label={t("actions.cancelFor", { name: run.document_name })}
        disabled={!canCancelRun(run)}
        onClick={() => onCancel(run)}
        tooltip={t("actions.cancelShort")}
        variant="secondary"
      >
        <XCircleIcon />
      </IconTooltipButton>
      <DropdownMenu>
        <IconTooltipButton
          aria-label={t("actions.moreFor", { name: run.document_name })}
          asChild
          tooltip={t("actions.more")}
          variant="secondary"
        >
          <DropdownMenuTrigger
            aria-label={t("actions.moreFor", { name: run.document_name })}
          >
            <MoreHorizontalIcon />
          </DropdownMenuTrigger>
        </IconTooltipButton>
        <DropdownMenuContent align="end" className="min-w-64">
          <DropdownMenuSub>
            <DropdownMenuSubTrigger
              aria-label={t("actions.rerunWithPipeline", {
                name: run.document_name,
              })}
              disabled={!rerunnable || pending || pipelinesLoading}
            >
              <WorkflowIcon />
              {t("actions.rerunWithPipelineShort")}
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent className="min-w-64">
              {pipelines.map((pipeline) => (
                <DropdownMenuItem
                  key={pipeline.id}
                  onSelect={() => onRerun(run, pipeline.id)}
                >
                  {pipeline.name} · v{pipeline.publishedVersion}
                </DropdownMenuItem>
              ))}
              {pipelines.length === 0 ? (
                <DropdownMenuItem disabled>
                  {t("actions.noPipelines")}
                </DropdownMenuItem>
              ) : null}
            </DropdownMenuSubContent>
          </DropdownMenuSub>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
