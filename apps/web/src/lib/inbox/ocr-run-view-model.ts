import type {
  OcrPipelineRun,
  OcrPipelineRunListEnvelope,
  OcrPipelineRunStatus,
} from "./types";

export interface OcrPipelineRunProgress {
  completedSteps: number;
  percent: number;
  totalSteps: number;
}

const TERMINAL_OCR_RUN_STATUSES = new Set<OcrPipelineRunStatus>([
  "failed",
  "partial_failed",
  "succeeded",
  "cancelled",
]);
export const OCR_PIPELINE_RUN_REFETCH_INTERVAL_MS = 3_000;

export function replaceOcrPipelineRunInHistory(
  history: OcrPipelineRunListEnvelope | undefined,
  replacement: OcrPipelineRun,
): OcrPipelineRunListEnvelope | undefined {
  if (!history) {
    return history;
  }
  return {
    ...history,
    data: {
      ...history.data,
      runs: history.data.runs.map((run) =>
        run.id === replacement.id ? replacement : run,
      ),
    },
  };
}

export function isTerminalOcrPipelineRunStatus(
  status: OcrPipelineRunStatus,
): boolean {
  return TERMINAL_OCR_RUN_STATUSES.has(status);
}

export function getOcrPipelineRunHistoryRefetchInterval(
  status: OcrPipelineRunStatus | null,
): number | false {
  return status === "pending" || status === "running" || status === "cancelling"
    ? OCR_PIPELINE_RUN_REFETCH_INTERVAL_MS
    : false;
}

export function getOcrPipelineRunProgress(
  run: OcrPipelineRun,
): OcrPipelineRunProgress {
  const totalSteps = run.steps.length;

  if (totalSteps === 0) {
    return {
      completedSteps: isTerminalOcrPipelineRunStatus(run.status) ? 1 : 0,
      percent: isTerminalOcrPipelineRunStatus(run.status) ? 100 : 0,
      totalSteps,
    };
  }

  const completedSteps = run.steps.filter((step) =>
    ["failed", "skipped", "succeeded"].includes(step.status),
  ).length;

  return {
    completedSteps,
    percent: Math.round((completedSteps / totalSteps) * 100),
    totalSteps,
  };
}

export function hasActiveOcrPipelineRun(
  runs: readonly OcrPipelineRun[],
): boolean {
  return runs.some((run) => !isTerminalOcrPipelineRunStatus(run.status));
}

export function selectActiveOcrPipelineRun(
  runs: readonly OcrPipelineRun[],
): OcrPipelineRun | null {
  return (
    runs.find((run) => !isTerminalOcrPipelineRunStatus(run.status)) ?? null
  );
}

export function selectLatestOcrPipelineRun(
  runs: readonly OcrPipelineRun[],
): OcrPipelineRun | null {
  if (runs.length === 0) {
    return null;
  }

  return [...runs].sort((first, second) => {
    const firstTime = Date.parse(first.createdAt);
    const secondTime = Date.parse(second.createdAt);

    if (secondTime !== firstTime) {
      return secondTime - firstTime;
    }

    return second.updatedAt.localeCompare(first.updatedAt);
  })[0];
}
