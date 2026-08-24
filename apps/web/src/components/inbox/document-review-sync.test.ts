import assert from "node:assert/strict";
import test from "node:test";

import type { DocumentReview } from "@/lib/review/types";

import {
  getDocumentReviewPresentationKind,
  getDocumentReviewRefetchInterval,
  REVIEW_REFETCH_INTERVAL_MS,
} from "./document-review-sync";

const MOCK_REVIEW: DocumentReview = {
  approval: null,
  attributesAvailable: true,
  dataSource: "mock",
  documentId: "document-1",
  fields: [],
  processingStatus: "completed",
  qualityScore: null,
  reviewId: null,
  schemaVersion: 1,
  unavailableReasonCode: null,
  updatedAt: null,
  updatedByActorId: null,
  version: null,
};

test("shows pipeline-not-run instead of backend mock values when history is empty", () => {
  assert.equal(
    getDocumentReviewPresentationKind({
      historyError: false,
      historyPending: false,
      latestRunStatus: null,
      review: MOCK_REVIEW,
      runCount: 0,
    }),
    "not_run",
  );
});

test("polls review only after a successful run until pipeline data is ready", () => {
  assert.equal(getDocumentReviewRefetchInterval("running", "mock"), false);
  assert.equal(
    getDocumentReviewRefetchInterval("succeeded", "mock"),
    REVIEW_REFETCH_INTERVAL_MS,
  );
  assert.equal(
    getDocumentReviewRefetchInterval("succeeded", "pipeline"),
    false,
  );
  assert.equal(getDocumentReviewRefetchInterval("succeeded", "manual"), false);
  assert.equal(
    getDocumentReviewRefetchInterval("partial_failed", "mock"),
    false,
  );
  assert.equal(getDocumentReviewRefetchInterval("failed", "mock"), false);
});

test("shows only pipeline-backed attributes as ready verification results", () => {
  assert.equal(
    getDocumentReviewPresentationKind({
      historyError: false,
      historyPending: false,
      latestRunStatus: "running",
      review: MOCK_REVIEW,
      runCount: 1,
    }),
    "loading",
  );

  assert.equal(
    getDocumentReviewPresentationKind({
      historyError: false,
      historyPending: false,
      latestRunStatus: "failed",
      review: MOCK_REVIEW,
      runCount: 1,
    }),
    "unavailable",
  );

  assert.equal(
    getDocumentReviewPresentationKind({
      historyError: false,
      historyPending: false,
      latestRunStatus: "succeeded",
      review: {
        ...MOCK_REVIEW,
        dataSource: "pipeline",
      },
      runCount: 1,
    }),
    "ready",
  );

  assert.equal(
    getDocumentReviewPresentationKind({
      historyError: false,
      historyPending: false,
      latestRunStatus: "succeeded",
      review: {
        ...MOCK_REVIEW,
        dataSource: "manual",
      },
      runCount: 1,
    }),
    "ready",
  );
});
