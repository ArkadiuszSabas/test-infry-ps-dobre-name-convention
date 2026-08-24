"use client";

import { RefreshCwIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { InboxNotice } from "@/components/inbox/inbox-notice";
import {
  runStatusClassName,
  StepStatusIcon,
  stepStatusClassName,
} from "@/components/inbox/ocr-pipeline-run-status";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import type { OcrPipelineRun, OcrPipelineRunResult } from "@/lib/inbox/types";
import {
  getOcrPipelineRunProgress,
  isTerminalOcrPipelineRunStatus,
} from "@/lib/inbox/ocr-run-view-model";
import { getOcrPipelineRunLabel } from "@/lib/inbox/ocr-pipeline-run-label";
import { cn } from "@/lib/utils";

export interface OcrRunSummaryProps {
  formatDate: (value: string) => string;
  formatNumber: (
    value: number,
    options?: { maximumFractionDigits?: number },
  ) => string;
  isRefreshing: boolean;
  result: OcrPipelineRunResult | null;
  resultError: boolean;
  resultLoading: boolean;
  run: OcrPipelineRun;
}

export function OcrRunSummary({
  formatDate,
  formatNumber,
  isRefreshing,
  result,
  resultError,
  resultLoading,
  run,
}: OcrRunSummaryProps) {
  const t = useTranslations("Inbox.ocrRun");
  const progress = getOcrPipelineRunProgress(run);
  const pipelineLabel = getOcrPipelineRunLabel(run);
  const isTerminalRun = isTerminalOcrPipelineRunStatus(run.status);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className={runStatusClassName(run.status)} variant="outline">
          {t(`status.${run.status}`)}
        </Badge>
        <Badge variant="outline">
          {t(pipelineLabel.key, pipelineLabel.values)}
        </Badge>
        {isRefreshing ? (
          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
            <RefreshCwIcon className="size-3 animate-spin" />
            {t("refreshing")}
          </span>
        ) : null}
      </div>

      <dl className="grid grid-cols-[8rem_minmax(0,1fr)] gap-x-4 gap-y-2 text-sm">
        <RunDetailRow label={t("fields.started")}>
          {run.startedAt ? formatDate(run.startedAt) : t("fields.notStarted")}
        </RunDetailRow>
        <RunDetailRow label={t("fields.updated")}>
          {formatDate(run.updatedAt)}
        </RunDetailRow>
        {run.completedAt ? (
          <RunDetailRow label={t("fields.completed")}>
            {formatDate(run.completedAt)}
          </RunDetailRow>
        ) : null}
      </dl>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3 text-sm">
          <span className="font-medium text-foreground">
            {t("progress.label")}
          </span>
          <span className="text-muted-foreground">
            {progress.totalSteps > 0
              ? t("progress.steps", {
                  completed: progress.completedSteps,
                  total: progress.totalSteps,
                })
              : t("progress.noSteps")}
          </span>
        </div>
        <Progress value={progress.percent} />
      </div>

      {run.steps.length > 0 ? (
        <RunStepList formatNumber={formatNumber} run={run} />
      ) : null}

      {run.diagnostics.length > 0 ? <RunDiagnostics run={run} /> : null}

      {run.error ? (
        <InboxNotice
          description={`${run.error.code}: ${run.error.message}`}
          title={t("runErrorTitle")}
          tone="danger"
        />
      ) : null}

      <RunResultState
        isTerminalRun={isTerminalRun}
        result={result}
        resultError={resultError}
        resultLoading={resultLoading}
        run={run}
      />
    </div>
  );
}

function RunStepList({
  formatNumber,
  run,
}: {
  formatNumber: (
    value: number,
    options?: { maximumFractionDigits?: number },
  ) => string;
  run: OcrPipelineRun;
}) {
  const t = useTranslations("Inbox.ocrRun");

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-foreground">
        {t("steps.title")}
      </h3>
      <ul className="divide-y divide-border text-sm">
        {run.steps.map((step) => (
          <li className="flex items-start gap-3 py-2" key={step.stepId}>
            <StepStatusIcon status={step.status} />
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="min-w-0 truncate font-medium text-foreground">
                  {step.displayName}
                </span>
                <Badge
                  className={stepStatusClassName(step.status)}
                  variant="outline"
                >
                  {t(`stepStatus.${step.status}`)}
                </Badge>
              </div>
              <p className="break-all font-mono text-xs text-muted-foreground">
                {step.implementationId}
              </p>
              {step.durationSeconds !== null ? (
                <p className="text-xs text-muted-foreground">
                  {t("steps.duration", {
                    seconds: formatNumber(step.durationSeconds, {
                      maximumFractionDigits: 1,
                    }),
                  })}
                </p>
              ) : null}
              {step.error ? (
                <p className="text-sm leading-6 text-destructive">
                  {step.error.code}: {step.error.message}
                </p>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RunDiagnostics({ run }: { run: OcrPipelineRun }) {
  const t = useTranslations("Inbox.ocrRun");

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-foreground">
        {t("diagnostics.title")}
      </h3>
      <ul className="space-y-2 text-sm">
        {run.diagnostics.map((diagnostic) => (
          <li
            className="rounded-lg bg-muted/40 px-3 py-2 leading-6"
            key={`${diagnostic.code}-${diagnostic.stepId ?? diagnostic.path ?? diagnostic.message}`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                className={cn(
                  diagnostic.severity === "error"
                    ? "border-destructive/30 text-destructive"
                    : "border-amber-300 text-amber-700",
                )}
                variant="outline"
              >
                {t(`severity.${diagnostic.severity}`)}
              </Badge>
              <span className="font-mono text-xs text-muted-foreground">
                {diagnostic.code}
              </span>
            </div>
            <p className="mt-1 text-foreground">{diagnostic.message}</p>
            {diagnostic.stepId ? (
              <p className="text-xs text-muted-foreground">
                {t("diagnostics.step", { stepId: diagnostic.stepId })}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function RunResultState({
  isTerminalRun,
  result,
  resultError,
  resultLoading,
  run,
}: {
  isTerminalRun: boolean;
  result: OcrPipelineRunResult | null;
  resultError: boolean;
  resultLoading: boolean;
  run: OcrPipelineRun;
}) {
  const t = useTranslations("Inbox.ocrRun");

  if (!isTerminalRun) {
    return (
      <p className="text-sm leading-6 text-muted-foreground">
        {t("result.waiting")}
      </p>
    );
  }

  if (resultLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner className="size-4" />
        {t("result.loading")}
      </div>
    );
  }

  if (resultError) {
    return (
      <InboxNotice
        description={t("result.loadErrorDescription")}
        title={t("result.loadErrorTitle")}
        tone="danger"
      />
    );
  }

  if (result?.resultAvailable) {
    return (
      <InboxNotice
        description={t("result.availableDescription")}
        title={t("result.availableTitle")}
      />
    );
  }

  const reasonCode =
    result?.unavailableReasonCode ??
    run.resultUnavailableReasonCode ??
    "RESULT_NOT_AVAILABLE";

  return (
    <InboxNotice
      description={getResultUnavailableMessage(reasonCode, t)}
      title={t("result.unavailableTitle")}
    />
  );
}

function RunDetailRow({
  children,
  label,
}: {
  children: ReactNode;
  label: string;
}) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-foreground">{children}</dd>
    </>
  );
}

function getResultUnavailableMessage(
  reasonCode: string,
  t: ReturnType<typeof useTranslations>,
): string {
  switch (reasonCode) {
    case "RUN_NOT_FINISHED":
      return t("result.reasons.runNotFinished");
    case "LLMMAGIC_RUN_UNAVAILABLE":
      return t("result.reasons.llmMagicUnavailable");
    default:
      return t("result.reasons.generic", { code: reasonCode });
  }
}
