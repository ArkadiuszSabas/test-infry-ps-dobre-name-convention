import assert from "node:assert/strict";
import test from "node:test";

import {
  canSubmitDocumentDeletion,
  isCompletedDocumentDeletionImpact,
  isDocumentDeletionResume,
} from "./deletion-view-model";
import type { DocumentDeletionImpact } from "./types";

test("ready impact allows an explicit resume after ambiguous connector state", () => {
  const impact = deletionImpact("ambiguous");

  assert.equal(canSubmitDocumentDeletion(impact), true);
  assert.equal(isDocumentDeletionResume(impact), true);
});

test("completed deletion cannot be submitted again and reconciles as completed", () => {
  const impact = deletionImpact("completed");

  assert.equal(canSubmitDocumentDeletion(impact), false);
  assert.equal(isCompletedDocumentDeletionImpact(impact), true);
});

test("current connector preparation still blocks unsafe resume", () => {
  const impact = {
    ...deletionImpact("blocked"),
    preparation_status: "ambiguous",
  } satisfies DocumentDeletionImpact;

  assert.equal(canSubmitDocumentDeletion(impact), false);
});

function deletionImpact(
  state: NonNullable<DocumentDeletionImpact["operation"]>["state"],
): DocumentDeletionImpact {
  return {
    document_id: "document-1",
    policy: "preserve",
    preparation_status: "ready",
    warning_code: "EXTERNAL_CONNECTOR_ARTIFACTS_PRESERVED",
    error_code: null,
    preserved_artifact_labels: ["SharePoint", "WEBCON"],
    operation: {
      operation_id: "operation-1",
      document_id: "document-1",
      stage: state === "completed" ? "completed" : "requested",
      state,
      policy: "preserve",
      warning_code: "EXTERNAL_CONNECTOR_ARTIFACTS_PRESERVED",
      failure_stage: state === "completed" ? null : "connector",
      error_code: state === "completed" ? null : "DOCUMENT_DELETE_AMBIGUOUS",
      created_at: "2026-07-28T10:00:00Z",
      updated_at: "2026-07-28T10:01:00Z",
      completed_at: state === "completed" ? "2026-07-28T10:01:00Z" : null,
    },
  };
}
