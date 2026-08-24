import assert from "node:assert/strict";
import test from "node:test";

import type { CurrentActor } from "@/lib/auth/types";
import type { InboxDocument } from "@/lib/inbox/types";

import type { DocumentReview } from "./types";
import {
  buildReviewWorkspaceViewModel,
  formatFallbackStatusLabel,
} from "./view-model";

const actor: CurrentActor = {
  auth_providers: ["local"],
  email: "reviewer@example.test",
  permissions: ["documents.read", "documents.review"],
  provider: "local",
  roles: ["reviewer"],
  user_id: "reviewer-1",
};

test("buildReviewWorkspaceViewModel uses the versioned review contract", () => {
  const model = buildReviewWorkspaceViewModel({
    actor,
    document: documentFixture(),
    review: reviewFixture(),
  });

  assert.equal(model.isActiveVerifier, true);
  assert.equal(model.canEditReview, true);
  assert.equal(model.qualityScore, 0.75);
  assert.equal(model.version, 3);
  assert.equal(model.fields[0]?.label, "Contract number");
  assert.equal(model.fields[0]?.confidence, 0.96);
});

test("buildReviewWorkspaceViewModel keeps editing disabled without review permission", () => {
  const model = buildReviewWorkspaceViewModel({
    actor: { ...actor, permissions: ["documents.read"] },
    document: documentFixture(),
    review: reviewFixture(),
  });

  assert.equal(model.isActiveVerifier, false);
  assert.equal(model.canEditReview, false);
});

test("buildReviewWorkspaceViewModel keeps editing disabled for another active verifier", () => {
  const model = buildReviewWorkspaceViewModel({
    actor: { ...actor, user_id: "reviewer-2" },
    document: documentFixture(),
    review: reviewFixture(),
  });

  assert.equal(model.isActiveVerifier, false);
  assert.equal(model.canEditReview, false);
});

test("buildReviewWorkspaceViewModel lets an administrator edit without active assignment", () => {
  const model = buildReviewWorkspaceViewModel({
    actor: { ...actor, roles: ["admin"], user_id: "administrator-1" },
    document: documentFixture(),
    review: reviewFixture(),
  });

  assert.equal(model.isActiveVerifier, false);
  assert.equal(model.canEditReview, true);
});

test("formatFallbackStatusLabel formats unknown statuses", () => {
  assert.equal(
    formatFallbackStatusLabel("waiting_for_approval"),
    "Waiting For Approval",
  );
});

function reviewFixture(): DocumentReview {
  return {
    approval: {
      history: [],
      isCurrentActorActiveReviewer: true,
      runNumber: 1,
      status: "waiting_for_review",
      steps: [],
    },
    attributesAvailable: true,
    dataSource: "pipeline",
    documentId: "document-1",
    fields: [
      {
        attributeExternalId: "contract_number",
        attributeId: "attribute-1",
        confidence: 0.96,
        dataType: "string",
        displayOrder: 10,
        displayValue: "AGR-2026-001",
        id: "field-1",
        kind: "configured",
        label: "Contract number",
        manuallyEdited: false,
        required: true,
        requiresReview: false,
        reviewReasonCodes: [],
        sources: [],
        status: "present",
        validations: [],
        value: "AGR-2026-001",
        valueSource: "pipeline",
      },
    ],
    processingStatus: "completed",
    qualityScore: 0.75,
    reviewId: "review-1",
    schemaVersion: 2,
    unavailableReasonCode: null,
    updatedAt: "2026-07-15T10:00:00Z",
    updatedByActorId: "reviewer-1",
    version: 3,
  };
}

function documentFixture(): InboxDocument {
  return {
    archiveUrl: null,
    connector: "manual_upload",
    connectorCorrelationId: null,
    connectorName: "Manual upload",
    contentSizeBytes: 123,
    createdAt: "2026-06-16T10:00:00Z",
    documentTypeExternalId: "supplier_invoice",
    documentTypeId: "document-type-1",
    documentTypeName: "Supplier invoice",
    externalId: null,
    id: "document-1",
    metadataValues: { active_reviewer_user_id: "reviewer-1" },
    name: "supplier-invoice.pdf",
    originalFilename: "supplier-invoice.pdf",
    source: "manual_upload",
    status: "in_review",
    uploadedBy: null,
    updatedAt: "2026-06-16T10:00:00Z",
  };
}
