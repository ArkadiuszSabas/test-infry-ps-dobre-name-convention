import assert from "node:assert/strict";
import test from "node:test";

import type { ReviewFieldItem } from "./types";

import {
  addManualDraftField,
  createReviewDraft,
  createReviewEditSession,
  hasManualChange,
  isDraftDirty,
  removeDraftField,
  toSaveFields,
  updateDraftValue,
} from "./editor-state";

test("review edit session keeps the version captured with its draft", () => {
  const field = fieldFixture();
  const session = createReviewEditSession([field], 2);
  const newerServerVersion = 3;

  assert.equal(session.expectedVersion, 2);
  assert.notEqual(session.expectedVersion, newerServerVersion);
  assert.deepEqual(session.fields, createReviewDraft([field]));
});

test("editing a value marks the field as manual and keeps original confidence", () => {
  const draft = updateDraftValue(
    createReviewDraft([fieldFixture()]),
    "field-1",
    "changed",
  );
  const changed = draft[0];

  assert.ok(changed);
  assert.equal(changed.value, "changed");
  assert.equal(changed.valueSource, "manual");
  assert.equal(changed.confidence, 0.96);
  assert.equal(hasManualChange(changed), true);
  assert.equal(isDraftDirty([fieldFixture()], draft), true);
});

test("manual fields have no confidence and serialize with a null id", () => {
  const draft = addManualDraftField(
    createReviewDraft([fieldFixture()]),
    { dataType: "string", label: "Reference", value: "ABC" },
    "client-1",
  );
  const added = draft[1];

  assert.ok(added);
  assert.equal(added.kind, "manual");
  assert.equal(added.confidence, null);
  assert.deepEqual(toSaveFields(draft)[1], {
    dataType: "string",
    id: null,
    label: "Reference",
    value: "ABC",
  });
});

test("removing a field makes the complete-list draft dirty", () => {
  const original = [fieldFixture()];
  const draft = removeDraftField(createReviewDraft(original), "field-1");

  assert.equal(draft.length, 0);
  assert.equal(isDraftDirty(original, draft), true);
});

function fieldFixture(): ReviewFieldItem {
  return {
    attributeExternalId: "contract_number",
    attributeId: "attribute-1",
    confidence: 0.96,
    dataType: "string",
    displayOrder: 10,
    displayValue: "original",
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
    value: "original",
    valueSource: "pipeline",
  };
}
