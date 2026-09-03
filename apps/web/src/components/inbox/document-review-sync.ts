import type { OcrPipelineRunStatus } from "@/lib/inbox/types";
import type { DocumentReview, ReviewDataSource } from "@/lib/review/types";

export const REVIEW_REFETCH_INTERVAL_MS = 2_500;

export type DocumentReviewPresentationKind =
  | "loading"
  | "not_run"
  | "ready"
  | "unavailable";

interface DocumentReviewPresentationInput {
  historyError: boolean;
  historyPending: boolean;
  latestRunStatus: OcrPipelineRunStatus | null;
  review: DocumentReview;
  runCount: number;
}

export function getDocumentReviewPresentationKind({
  historyError,
  historyPending,
  latestRunStatus,
  review,
  runCount,
}: DocumentReviewPresentationInput): DocumentReviewPresentationKind {
  if (
    isReadyReviewDataSource(review.dataSource) &&
    review.attributesAvailable
  ) {
    return "ready";
  }

  if (historyPending) {
    return "loading";
  }

  if (historyError) {
    return "unavailable";
  }

  if (runCount === 0) {
    return "not_run";
  }

  if (
    latestRunStatus === "pending" ||
    latestRunStatus === "running" ||
    latestRunStatus === "cancelling"
  ) {
    return "loading";
  }

  if (getDocumentReviewRefetchInterval(latestRunStatus, review.dataSource)) {
    return "loading";
  }

  return "unavailable";
}

export function getDocumentReviewRefetchInterval(
  latestRunStatus: OcrPipelineRunStatus | null,
  reviewDataSource: ReviewDataSource | undefined,
): number | false {
  if (
    latestRunStatus === "succeeded" &&
    !isReadyReviewDataSource(reviewDataSource)
  ) {
    return REVIEW_REFETCH_INTERVAL_MS;
  }

  return false;
}

function isReadyReviewDataSource(
  reviewDataSource: ReviewDataSource | undefined,
): boolean {
  return reviewDataSource === "pipeline" || reviewDataSource === "manual";
}
