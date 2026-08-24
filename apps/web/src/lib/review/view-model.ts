import type { CurrentActor } from "@/lib/auth/types";
import type { InboxDocument } from "@/lib/inbox/types";

import type { DocumentReview, ReviewWorkspaceViewModel } from "./types";

export interface BuildReviewWorkspaceViewModelInput {
  actor: CurrentActor | null;
  document: InboxDocument;
  review: DocumentReview;
}

export function buildReviewWorkspaceViewModel({
  actor,
  document,
  review,
}: BuildReviewWorkspaceViewModelInput): ReviewWorkspaceViewModel {
  const activeReviewerUserId = getActiveReviewerUserId(document);
  const hasReviewPermission = Boolean(
    actor?.permissions.includes("documents.review"),
  );
  const isAdministrator = Boolean(actor?.roles.includes("admin"));
  const isAssignedReviewer = Boolean(
    actor && activeReviewerUserId && actor.user_id === activeReviewerUserId,
  );

  return {
    approval: review.approval,
    activeVerifier: actor,
    canEditReview:
      hasReviewPermission && (isAdministrator || isAssignedReviewer),
    document,
    fields: review.fields,
    isActiveVerifier: hasReviewPermission && isAssignedReviewer,
    qualityScore: review.qualityScore,
    reviewId: review.reviewId,
    version: review.version,
  };
}

function getActiveReviewerUserId(document: InboxDocument): string | null {
  const value = document.metadataValues.active_reviewer_user_id;
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

export function formatFallbackStatusLabel(status: string): string {
  return status
    .split(/[_\s-]+/u)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
