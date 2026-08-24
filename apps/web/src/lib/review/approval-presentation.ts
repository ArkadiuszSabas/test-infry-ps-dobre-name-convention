import type { ReviewApproval } from "./types";

export type ApprovalPresentationStatus =
  | "approved"
  | "inReview"
  | "pending"
  | "rejected";

export interface ApprovalPresentation {
  approvedCount: number;
  status: ApprovalPresentationStatus;
  totalCount: number;
}

export function canCurrentActorDecide(
  approval: ReviewApproval | null,
  isActiveVerifier: boolean,
): boolean {
  return approval?.isCurrentActorActiveReviewer ?? isActiveVerifier;
}

export function getApprovalPresentation(
  approval: ReviewApproval | null,
): ApprovalPresentation {
  const approvedCount =
    approval?.steps.filter((step) => step.status === "approved").length ?? 0;
  const totalCount = approval?.steps.length ?? 2;
  const lastDecision = approval?.history.at(-1);

  if (approval?.status === "approved" || approvedCount === totalCount) {
    return { approvedCount: totalCount, status: "approved", totalCount };
  }
  if (approval?.status === "in_review" || approvedCount > 0) {
    return { approvedCount, status: "inReview", totalCount };
  }
  if (
    approval?.status === "waiting_for_review" &&
    lastDecision?.decision === "rejected" &&
    lastDecision.runNumber === approval.runNumber - 1
  ) {
    return { approvedCount: 0, status: "rejected", totalCount };
  }
  return { approvedCount: 0, status: "pending", totalCount };
}

export function reviewerDisplayLabel(
  displayName: string | null,
  unassignedLabel: string,
): string {
  return displayName ?? unassignedLabel;
}

export function requiresDifferentSecondReviewer(
  approval: ReviewApproval | null,
): boolean {
  return (
    approval?.steps[0]?.status === "approved" &&
    approval.steps[1]?.status === "waiting"
  );
}
