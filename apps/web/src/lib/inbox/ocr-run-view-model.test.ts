import assert from "node:assert/strict";
import test from "node:test";

import type { OcrPipelineRun } from "./types";
import {
  getOcrPipelineRunHistoryRefetchInterval,
  getOcrPipelineRunProgress,
  hasActiveOcrPipelineRun,
  isTerminalOcrPipelineRunStatus,
  OCR_PIPELINE_RUN_REFETCH_INTERVAL_MS,
  selectActiveOcrPipelineRun,
  selectLatestOcrPipelineRun,
} from "./ocr-run-view-model";

test("OCR pipeline run progress counts terminal step states", () => {
  const run = ocrRunFixture({
    steps: [
      ocrStepFixture({ status: "succeeded", stepId: "preflight" }),
      ocrStepFixture({ status: "running", stepId: "ocr" }),
      ocrStepFixture({ status: "skipped", stepId: "normalization" }),
    ],
  });

  assert.deepEqual(getOcrPipelineRunProgress(run), {
    completedSteps: 2,
    percent: 67,
    totalSteps: 3,
  });
});

test("OCR pipeline run progress handles terminal runs without step trace", () => {
  assert.deepEqual(
    getOcrPipelineRunProgress(
      ocrRunFixture({ status: "succeeded", steps: [] }),
    ),
    { completedSteps: 1, percent: 100, totalSteps: 0 },
  );
  assert.deepEqual(
    getOcrPipelineRunProgress(ocrRunFixture({ status: "running", steps: [] })),
    { completedSteps: 0, percent: 0, totalSteps: 0 },
  );
});

test("OCR pipeline terminal status helper matches product statuses", () => {
  assert.equal(isTerminalOcrPipelineRunStatus("pending"), false);
  assert.equal(isTerminalOcrPipelineRunStatus("running"), false);
  assert.equal(isTerminalOcrPipelineRunStatus("succeeded"), true);
  assert.equal(isTerminalOcrPipelineRunStatus("partial_failed"), true);
  assert.equal(isTerminalOcrPipelineRunStatus("failed"), true);
});

test("OCR pipeline history polling runs only while the latest run is active", () => {
  assert.equal(
    getOcrPipelineRunHistoryRefetchInterval("pending"),
    OCR_PIPELINE_RUN_REFETCH_INTERVAL_MS,
  );
  assert.equal(
    getOcrPipelineRunHistoryRefetchInterval("running"),
    OCR_PIPELINE_RUN_REFETCH_INTERVAL_MS,
  );
  assert.equal(getOcrPipelineRunHistoryRefetchInterval("succeeded"), false);
  assert.equal(
    getOcrPipelineRunHistoryRefetchInterval("partial_failed"),
    false,
  );
  assert.equal(getOcrPipelineRunHistoryRefetchInterval("failed"), false);
  assert.equal(getOcrPipelineRunHistoryRefetchInterval(null), false);
});

test("active OCR pipeline run helpers prefer non-terminal history", () => {
  const failed = ocrRunFixture({ id: "failed-run", status: "failed" });
  const running = ocrRunFixture({ id: "running-run", status: "running" });
  const succeeded = ocrRunFixture({ id: "succeeded-run", status: "succeeded" });

  assert.equal(hasActiveOcrPipelineRun([failed, running, succeeded]), true);
  assert.equal(
    selectActiveOcrPipelineRun([failed, running, succeeded])?.id,
    "running-run",
  );
  assert.equal(hasActiveOcrPipelineRun([failed, succeeded]), false);
  assert.equal(selectActiveOcrPipelineRun([failed, succeeded]), null);
});

test("latest OCR pipeline run is selected by creation timestamp", () => {
  const olderButUpdated = ocrRunFixture({
    createdAt: "2026-07-01T09:00:00Z",
    id: "older-run",
    updatedAt: "2026-07-01T09:10:00Z",
  });
  const newerCreated = ocrRunFixture({
    createdAt: "2026-07-01T09:03:00Z",
    id: "newer-run",
    updatedAt: "2026-07-01T09:03:00Z",
  });

  assert.equal(
    selectLatestOcrPipelineRun([olderButUpdated, newerCreated])?.id,
    "newer-run",
  );
  assert.equal(selectLatestOcrPipelineRun([]), null);
});

function ocrRunFixture(
  overrides: Partial<OcrPipelineRun> = {},
): OcrPipelineRun {
  return {
    catalogHash: "catalog-hash-v1",
    catalogVersion: "catalog-v1",
    completedAt: null,
    createdAt: "2026-07-01T09:00:00Z",
    diagnostics: [],
    documentId: "33333333-3333-3333-3333-333333333333",
    error: null,
    id: "99999999-9999-9999-9999-999999999999",
    metrics: {},
    pipelineId: "77777777-7777-7777-7777-777777777777",
    pipelineName: "Invoice OCR",
    pipelineVersion: 1,
    resultAvailability: "not_available",
    resultUnavailableReasonCode: "RUN_NOT_FINISHED",
    startedAt: null,
    status: "pending",
    steps: [ocrStepFixture()],
    updatedAt: "2026-07-01T09:00:00Z",
    ...overrides,
  };
}

function ocrStepFixture(
  overrides: Partial<OcrPipelineRun["steps"][number]> = {},
): OcrPipelineRun["steps"][number] {
  return {
    displayName: "Prepare document",
    durationSeconds: null,
    error: null,
    implementationId: "document.preflight.prepare",
    metrics: {},
    status: "pending",
    stepId: "preflight",
    stepType: "preflight",
    ...overrides,
  };
}
