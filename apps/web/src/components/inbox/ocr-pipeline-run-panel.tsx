"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PlayIcon, XCircleIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";

import { InboxNotice } from "@/components/inbox/inbox-notice";
import { OcrResultSection } from "@/components/inbox/inbox-ocr-result-section";
import { RunHistoryList } from "@/components/inbox/ocr-pipeline-run-history-list";
import {
  getOcrPipelineRunStartDisabledReason,
  getOcrPipelineRunStartErrorMessage,
} from "@/components/inbox/ocr-pipeline-run-start-guards";
import { OcrRunSummary } from "@/components/inbox/ocr-pipeline-run-summary";
import { OcrPipelineSelector } from "@/components/inbox/ocr-pipeline-selector";
import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import { Spinner } from "@/components/ui/spinner";
import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { inboxClient } from "@/lib/inbox/api";
import {
  documentOcrPipelineRunsQueryOptions,
  inboxQueryKeys,
  ocrPipelineRunResultQueryOptions,
  publishedOcrPipelinesQueryOptions,
} from "@/lib/inbox/query-options";
import type {
  InboxDocument,
  OcrPipelineRun,
  OcrPipelineRunListEnvelope,
  PublishedOcrPipelineOption,
} from "@/lib/inbox/types";
import {
  hasActiveOcrPipelineRun,
  isTerminalOcrPipelineRunStatus,
  replaceOcrPipelineRunInHistory,
  selectActiveOcrPipelineRun,
  selectLatestOcrPipelineRun,
} from "@/lib/inbox/ocr-run-view-model";
const EMPTY_OCR_PIPELINE_RUNS: readonly OcrPipelineRun[] = [];
const EMPTY_PUBLISHED_PIPELINES: readonly PublishedOcrPipelineOption[] = [];

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
  const [cancelDialogTarget, setCancelDialogTarget] = useState<{
    documentId: string;
    runId: string;
  } | null>(null);
  const [selectedPipeline, setSelectedPipeline] = useState<{
    documentId: string;
    pipelineId: string;
  } | null>(null);
  const canCreateRuns = Boolean(
    actor?.permissions.includes("documents.create"),
  );
  const selectedRunId =
    selectedRun?.documentId === document.id ? selectedRun.runId : null;

  const historyQuery = useQuery(
    documentOcrPipelineRunsQueryOptions(document.id, false),
  );
  const pipelinesQuery = useQuery(
    publishedOcrPipelinesQueryOptions(canCreateRuns && !readOnly),
  );
  const publishedPipelines =
    pipelinesQuery.data?.data.pipelines ?? EMPTY_PUBLISHED_PIPELINES;
  const defaultPipeline =
    publishedPipelines.find((pipeline) => pipeline.isDefault) ??
    publishedPipelines[0] ??
    null;
  const selectedPipelineId =
    selectedPipeline?.documentId === document.id &&
    publishedPipelines.some(
      (pipeline) => pipeline.id === selectedPipeline.pipelineId,
    )
      ? selectedPipeline.pipelineId
      : (defaultPipeline?.id ?? null);
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
    mutationFn: (pipelineId: string) =>
      runCsrfProtectedAction((csrfToken) =>
        inboxClient.startDocumentOcrPipelineRun(document.id, {
          csrfToken,
          pipelineId,
        }),
      ),
    onSuccess: async (run) => {
      setSelectedRun({ documentId: document.id, runId: run.id });
      await queryClient.invalidateQueries({
        queryKey: inboxQueryKeys.documentOcrPipelineRuns(document.id),
      });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (runId: string) =>
      runCsrfProtectedAction((csrfToken) =>
        inboxClient.cancelOcrPipelineRun(runId, { csrfToken }),
      ),
    onSuccess: (run) => {
      setCancelDialogTarget(null);
      setSelectedRun({ documentId: document.id, runId: run.id });
      queryClient.setQueryData<OcrPipelineRunListEnvelope>(
        inboxQueryKeys.documentOcrPipelineRuns(document.id),
        (current) => replaceOcrPipelineRunInHistory(current, run),
      );
      void queryClient.invalidateQueries({
        queryKey: inboxQueryKeys.documentOcrPipelineRuns(document.id),
      });
    },
  });
  const resetStartMutation = startMutation.reset;
  const resetCancelMutation = cancelMutation.reset;

  useEffect(() => {
    resetStartMutation();
    resetCancelMutation();
  }, [document.id, currentRun?.id, resetCancelMutation, resetStartMutation]);

  const knownRuns = useMemo(
    () =>
      currentRun && !historyRuns.some((run) => run.id === currentRun.id)
        ? [currentRun, ...historyRuns]
        : historyRuns,
    [currentRun, historyRuns],
  );
  const activeRunInProgress = hasActiveOcrPipelineRun(knownRuns);
  const startDisabledReason = getOcrPipelineRunStartDisabledReason({
    activeRunInProgress,
    canCreateRuns,
    document,
    historyUnavailable: historyQuery.isError,
    historyLoading: historyQuery.isPending,
    noPublishedPipelines:
      !pipelinesQuery.isPending &&
      !pipelinesQuery.isError &&
      publishedPipelines.length === 0,
    pipelinesLoading: pipelinesQuery.isPending,
    pipelinesUnavailable: pipelinesQuery.isError,
    selectedPipelineMissing: selectedPipelineId === null,
    t,
  });
  const startDisabled = Boolean(startDisabledReason) || startMutation.isPending;
  const startError = startMutation.isError
    ? getOcrPipelineRunStartErrorMessage(startMutation.error, t)
    : null;
  const canCancelRun =
    canCreateRuns &&
    (currentRun?.status === "pending" || currentRun?.status === "running");
  const cancellationInProgress = currentRun?.status === "cancelling";
  const retryRun =
    !activeRunInProgress &&
    (latestHistoryRun?.status === "failed" ||
      latestHistoryRun?.status === "cancelled");

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
          <div className="flex flex-wrap gap-2">
            {canCancelRun || cancellationInProgress ? (
              <Button
                disabled={cancellationInProgress || cancelMutation.isPending}
                onClick={() => {
                  resetCancelMutation();
                  if (currentRun) {
                    setCancelDialogTarget({
                      documentId: document.id,
                      runId: currentRun.id,
                    });
                  }
                }}
                size="sm"
                type="button"
                variant="outline"
              >
                {cancelMutation.isPending || cancellationInProgress ? (
                  <Spinner data-icon="inline-start" />
                ) : (
                  <XCircleIcon data-icon="inline-start" />
                )}
                {cancellationInProgress
                  ? t("actions.cancelling")
                  : t("actions.cancel")}
              </Button>
            ) : null}
            <Button
              disabled={startDisabled}
              onClick={() => {
                resetCancelMutation();
                if (selectedPipelineId) {
                  startMutation.mutate(selectedPipelineId);
                }
              }}
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
                : retryRun
                  ? t("actions.retry")
                  : t("actions.start")}
            </Button>
            <OcrPipelineSelector
              disabled={
                startMutation.isPending ||
                activeRunInProgress ||
                !canCreateRuns ||
                pipelinesQuery.isPending ||
                pipelinesQuery.isError ||
                publishedPipelines.length === 0
              }
              loading={pipelinesQuery.isPending}
              onValueChange={(pipelineId) =>
                setSelectedPipeline({ documentId: document.id, pipelineId })
              }
              pipelines={publishedPipelines}
              value={selectedPipelineId}
            />
          </div>
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

      <ConfirmActionDialog
        cancelLabel={t("actions.keepRun")}
        confirmLabel={t("actions.cancel")}
        description={t("actions.cancelConfirm")}
        error={
          cancelMutation.isError ? (
            <InboxNotice
              description={t("actions.cancelErrorDescription")}
              title={t("actions.cancelErrorTitle")}
              tone="danger"
            />
          ) : undefined
        }
        isPending={cancelMutation.isPending}
        onConfirm={() => {
          if (!cancelDialogTarget) {
            return;
          }
          resetStartMutation();
          cancelMutation.mutate(cancelDialogTarget.runId);
        }}
        onOpenChange={(open) => {
          if (cancelMutation.isPending) {
            return;
          }
          if (!open) {
            setCancelDialogTarget(null);
            resetCancelMutation();
          }
        }}
        open={
          cancelDialogTarget?.documentId === document.id &&
          cancelDialogTarget.runId === currentRun?.id &&
          canCancelRun
        }
        title={t("actions.cancelTitle")}
      />
    </section>
  );
}
