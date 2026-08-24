import type { DocumentDeletionImpact } from "./types";

export function canSubmitDocumentDeletion(
  impact: DocumentDeletionImpact | undefined,
): boolean {
  return Boolean(
    impact &&
    impact.preparation_status === "ready" &&
    impact.policy !== "block" &&
    impact.operation?.state !== "completed",
  );
}

export function isCompletedDocumentDeletionImpact(
  impact: DocumentDeletionImpact | undefined,
): boolean {
  return impact?.operation?.state === "completed";
}

export function isDocumentDeletionResume(
  impact: DocumentDeletionImpact | undefined,
): boolean {
  return Boolean(impact?.operation && impact.operation.state !== "completed");
}
