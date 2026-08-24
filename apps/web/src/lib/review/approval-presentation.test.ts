import assert from "node:assert/strict";
import test from "node:test";

import type { ReviewApproval } from "./types";
import {
  canCurrentActorDecide,
  getApprovalPresentation,
  requiresDifferentSecondReviewer,
  reviewerDisplayLabel,
} from "./approval-presentation";

const ACTIVE_APPROVAL: ReviewApproval = {
  history: [],
  isCurrentActorActiveReviewer: true,
  runNumber: 1,
  status: "in_review",
  steps: [
    {
      comment: null,
      decidedAt: "2026-07-21T10:00:00Z",
      number: 1,
      reviewerActorId: "internal-id-1",
      reviewerDisplayName: "Anna Kowalska",
      status: "approved",
    },
    {
      comment: null,
      decidedAt: null,
      number: 2,
      reviewerActorId: null,
      reviewerDisplayName: null,
      status: "waiting",
    },
  ],
};

test("approval actions are available only to the active reviewer", () => {
  assert.equal(canCurrentActorDecide(null, false), false);
  assert.equal(canCurrentActorDecide(null, true), true);
  assert.equal(canCurrentActorDecide(ACTIVE_APPROVAL, false), true);
  assert.equal(
    canCurrentActorDecide(
      { ...ACTIVE_APPROVAL, isCurrentActorActiveReviewer: false },
      true,
    ),
    false,
  );
});

test("approval presentation reports workflow states and progress", () => {
  assert.deepEqual(getApprovalPresentation(null), {
    approvedCount: 0,
    status: "pending",
    totalCount: 2,
  });
  assert.deepEqual(getApprovalPresentation(ACTIVE_APPROVAL), {
    approvedCount: 1,
    status: "inReview",
    totalCount: 2,
  });
  assert.deepEqual(
    getApprovalPresentation({
      ...ACTIVE_APPROVAL,
      status: "approved",
      steps: ACTIVE_APPROVAL.steps.map((step) => ({
        ...step,
        status: "approved",
      })),
    }),
    { approvedCount: 2, status: "approved", totalCount: 2 },
  );
  assert.deepEqual(
    getApprovalPresentation({
      ...ACTIVE_APPROVAL,
      history: [
        {
          actorDisplayName: "Anna Kowalska",
          actorId: "internal-id-1",
          comment: "Incorrect amount",
          decidedAt: "2026-07-21T10:05:00Z",
          decision: "rejected",
          runNumber: 1,
          stepNumber: 2,
        },
      ],
      runNumber: 2,
      status: "waiting_for_review",
      steps: ACTIVE_APPROVAL.steps.map((step) => ({
        ...step,
        decidedAt: null,
        reviewerActorId: null,
        reviewerDisplayName: null,
        status: "waiting",
      })),
    }),
    { approvedCount: 0, status: "rejected", totalCount: 2 },
  );
});

test("approval presentation supports a one-person workflow", () => {
  const singleApproval: ReviewApproval = {
    ...ACTIVE_APPROVAL,
    status: "waiting_for_review",
    steps: [
      {
        ...ACTIVE_APPROVAL.steps[0],
        decidedAt: null,
        reviewerActorId: null,
        reviewerDisplayName: null,
        status: "waiting",
      },
    ],
  };

  assert.deepEqual(getApprovalPresentation(singleApproval), {
    approvedCount: 0,
    status: "pending",
    totalCount: 1,
  });
  assert.deepEqual(
    getApprovalPresentation({
      ...singleApproval,
      status: "approved",
      steps: [
        {
          ...singleApproval.steps[0],
          decidedAt: "2026-07-21T10:00:00Z",
          reviewerActorId: "internal-id-1",
          status: "approved",
        },
      ],
    }),
    { approvedCount: 1, status: "approved", totalCount: 1 },
  );
});

test("approval panel renders safe reviewer names and explains the different-person rule", () => {
  assert.equal(
    reviewerDisplayLabel("Anna Kowalska", "Unassigned reviewer"),
    "Anna Kowalska",
  );
  assert.equal(
    reviewerDisplayLabel(null, "Unassigned reviewer"),
    "Unassigned reviewer",
  );
  assert.equal(requiresDifferentSecondReviewer(ACTIVE_APPROVAL), true);
  assert.equal(
    requiresDifferentSecondReviewer({
      ...ACTIVE_APPROVAL,
      steps: [
        { ...ACTIVE_APPROVAL.steps[0], status: "waiting" },
        ACTIVE_APPROVAL.steps[1],
      ],
    }),
    false,
  );
});
