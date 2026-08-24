"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PlayIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { InboxNotice } from "@/components/inbox/inbox-notice";
import { OcrResultSection } from "@/components/inbox/inbox-ocr-result-section";
import { RunHistoryList } from "@/components/inbox/ocr-pipeline-run-history-list";
import { OcrRunSummary } from "@/components/inbox/ocr-pipeline-run-summary";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { isApiError } from "@/lib/api/errors";
import { inboxClient } from "@/lib/inbox/api";
import {
  documentOcrPipelineRunsQueryOptions,
  inboxQueryKeys,
  ocrPipelineRunResultQueryOptions,
} from "@/lib/inbox/query-options";
import type { InboxDocument, OcrPipelineRun } from "@/lib/inbox/types";
import {
  hasActiveOcrPipelineRun,
  isTerminalOcrPipelineRunStatus,
  selectActiveOcrPipelineRun,
  selectLatestOcrPipelineRun,
} from "@/lib/inbox/ocr-run-view-model";
const EMPTY_OCR_PIPELINE_RUNS: readonly OcrPipelineRun[] = [];

export interface OcrPipelineRunPanelProps {
  document: InboxDocument;
  formatDate: (value: string) => string;
  formatNumber: (
    value: number,
    options?: { maximumFractionDigits?: number },
  ) => string;
  readOnly?: boolean;
}

export function OcrPipelineRunPanel({
  document,
  formatDate,
  formatNumber,
  readOnly = false,
}: OcrPipelineRunPanelProps) {
  const t = useTranslations("Inbox.ocrRun");
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const { actor } = useCurrentActor();
  const [selectedRun, setSelectedRun] = useState<{
    documentId: string;
    runId: string;
  } | null>(null);
  const canCreateRuns = Boolean(
    actor?.permissions.includes("documents.create"),
  );
  const selectedRunId =
    selectedRun?.documentId === document.id ? selectedRun.runId : null;

  const historyQuery = useQuery(
    documentOcrPipelineRunsQueryOptions(document.id, false),
  );
  const historyRuns = historyQuery.data?.data.runs ?? EMPTY_OCR_PIPELINE_RUNS;
  const selectedHistoryRun = useMemo(
    () =>
      selectedRunId
        ? (historyRuns.find((run) => run.id === selectedRunId) ?? null)
        : null,
    [historyRuns, selectedRunId],
  );
  const activeHistoryRun = useMemo(
    () => selectActiveOcrPipelineRun(historyRuns),
    [historyRuns],
  );
  const latestHistoryRun = useMemo(
    () => selectLatestOcrPipelineRun(historyRuns),
    [historyRuns],
  );
  const selectedRunPendingHistoryId =
    selectedRunId && !selectedHistoryRun ? selectedRunId : null;
  const preferredHistoryRun =
    activeHistoryRun ?? selectedHistoryRun ?? latestHistoryRun;
  const activeRunId =
    selectedRunPendingHistoryId ?? preferredHistoryRun?.id ?? "";
  const currentRun =
    historyRuns.find((run) => run.id === activeRunId) ?? preferredHistoryRun;
  const isTerminalRun = currentRun
    ? isTerminalOcrPipelineRunStatus(currentRun.status)
    : false;

  const resultQuery = useQuery(
    ocrPipelineRunResultQueryOptions(currentRun?.id ?? "", isTerminalRun),
  );
  const currentRunResult = resultQuery.data?.data ?? null;

  const startMutation = useMutation({
    mutationFn: () =>
      runCsrfProtectedAction((csrfToken) =>
        inboxClient.startDocumentOcrPipelineRun(document.id, { csrfToken }),
      ),
    onSuccess: async (run) => {
      setSelectedRun({ documentId: document.id, runId: run.id });
      await queryClient.invalidateQueries({
        queryKey: inboxQueryKeys.documentOcrPipelineRuns(document.id),
      });
    },
  });

  const knownRuns = useMemo(
    () =>
      currentRun && !historyRuns.some((run) => run.id === currentRun.id)
        ? [currentRun, ...historyRuns]
        : historyRuns,
    [currentRun, historyRuns],
  );
  const activeRunInProgress = hasActiveOcrPipelineRun(knownRuns);
  const startDisabledReason = getStartDisabledReason({
    activeRunInProgress,
    canCreateRuns,
    document,
    historyUnavailable: historyQuery.isError,
    historyLoading: historyQuery.isPending,
    t,
  });
  const startDisabled = Boolean(startDisabledReason) || startMutation.isPending;
  const startError = startMutation.isError
    ? getStartErrorMessage(startMutation.error, t)
    : null;

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <h2 className="text-xs font-medium uppercase text-muted-foreground">
            {t("title")}
          </h2>
          <p className="text-sm leading-6 text-muted-foreground">
            {t("description")}
          </p>
        </div>
        {!readOnly ? (
          <Button
            disabled={startDisabled}
            onClick={() => startMutation.mutate()}
            size="sm"
            type="button"
          >
            {startMutation.isPending ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <PlayIcon data-icon="inline-start" />
            )}
            {startMutation.isPending
              ? t("actions.starting")
              : t("actions.start")}
          </Button>
        ) : null}
      </div>

      {!readOnly && startDisabledReason ? (
        <p className="text-sm leading-6 text-muted-foreground">
          {startDisabledReason}
        </p>
      ) : null}

      {startError ? (
        <InboxNotice
          description={startError.description}
          title={startError.title}
          tone="danger"
        />
      ) : null}

      {historyQuery.isPending ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner className="size-4" />
          {t("history.loading")}
        </div>
      ) : null}

      {historyQuery.isError ? (
        <InboxNotice
          description={t("history.loadErrorDescription")}
          title={t("history.loadErrorTitle")}
          tone="danger"
        />
      ) : null}

      {currentRun ? (
        <>
          <OcrRunSummary
            formatDate={formatDate}
            formatNumber={formatNumber}
            isRefreshing={historyQuery.isFetching && !historyQuery.isPending}
            result={currentRunResult}
            resultError={resultQuery.isError}
            resultLoading={resultQuery.isPending && isTerminalRun}
            run={currentRun}
          />
          <OcrResultSection
            formatNumber={formatNumber}
            result={currentRunResult}
            resultError={resultQuery.isError}
            resultLoading={resultQuery.isPending && isTerminalRun}
            run={currentRun}
          />
        </>
      ) : null}

      {!activeRunId &&
      !currentRun &&
      !historyQuery.isPending &&
      !historyQuery.isError ? (
        <div className="rounded-lg bg-muted/40 px-3 py-2 text-sm leading-6 text-muted-foreground">
          <p className="font-medium text-foreground">{t("empty.title")}</p>
          <p>{t("empty.description")}</p>
        </div>
      ) : null}

      {historyRuns.length > 1 ? (
        <RunHistoryList
          activeRunId={activeRunId}
          formatDate={formatDate}
          onSelectRun={(runId) =>
            setSelectedRun({ documentId: document.id, runId })
          }
          runs={historyRuns}
        />
      ) : null}
    </section>
  );
}

function getStartDisabledReason({
  activeRunInProgress,
  canCreateRuns,
  document,
  historyUnavailable,
  historyLoading,
  t,
}: {
  activeRunInProgress: boolean;
  canCreateRuns: boolean;
  document: InboxDocument;
  historyUnavailable: boolean;
  historyLoading: boolean;
  t: ReturnType<typeof useTranslations>;
}): string | null {
  if (!canCreateRuns) {
    return t("disabled.permission");
  }

  if (document.contentSizeBytes === null) {
    return t("disabled.unknownSize");
  }

  if (historyLoading) {
    return t("disabled.historyLoading");
  }

  if (historyUnavailable) {
    return t("disabled.historyUnavailable");
  }

  if (activeRunInProgress) {
    return t("disabled.runInProgress");
  }

  return null;
}

function getStartErrorMessage(
  error: unknown,
  t: ReturnType<typeof useTranslations>,
): { description: string; title: string } {
  if (!isApiError(error)) {
    return {
      description: t("errors.genericStartDescription"),
      title: t("errors.genericStartTitle"),
    };
  }

  const translationKey = startErrorTranslationKey(error.code);

  return {
    description: translationKey
      ? t(`errors.${translationKey}.description`)
      : error.message,
    title: translationKey
      ? t(`errors.${translationKey}.title`)
      : t("errors.apiTitle"),
  };
}

function startErrorTranslationKey(code: string): string | null {
  switch (code) {
    case "OCR_PIPELINE_RUN_NO_PUBLISHED_DEFAULT":
      return "noPublishedDefault";
    case "OCR_PIPELINE_RUN_PIPELINE_NOT_RUNNABLE":
      return "pipelineNotRunnable";
    case "OCR_PIPELINE_RUN_DOCUMENT_SIZE_UNKNOWN":
      return "documentSizeUnknown";
    case "OCR_PIPELINE_RUN_LIMIT_EXCEEDED":
      return "limitExceeded";
    case "OCR_PIPELINE_RUN_ALREADY_ACTIVE":
      return "alreadyActive";
    case "OCR_PIPELINE_RUN_LLMMAGIC_UNAVAILABLE":
      return "llmMagicUnavailable";
    case "OCR_PIPELINE_RUN_DOCUMENT_NOT_FOUND":
      return "documentNotFound";
    default:
      return null;
  }
}
