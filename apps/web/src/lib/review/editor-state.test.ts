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

test("editing a value clears value-derived reason badges but retains configuration reasons", () => {
  const field = {
    ...fieldFixture(),
    requiresReview: true,
    reviewReasonCodes: [
      "VALUE_FROM_SOURCE_SYSTEM",
      "METADATA_CONTRADICTED",
      "CONFLICTING_VALUES",
      "ATTRIBUTE_MAPPING_MISSING",
    ],
    status: "conflicting" as const,
  };

  const [changed] = updateDraftValue(
    createReviewDraft([field]),
    "field-1",
    "changed",
  );

  assert.ok(changed);
  assert.equal(changed.status, "present");
  assert.equal(changed.requiresReview, false);
  assert.deepEqual(changed.reviewReasonCodes, ["ATTRIBUTE_MAPPING_MISSING"]);
});

test("returning to the original value restores the original review state", () => {
  const original = {
    ...fieldFixture(),
    requiresReview: true,
    reviewReasonCodes: ["VALUE_FROM_SOURCE_SYSTEM", "CONFLICTING_VALUES"],
    status: "conflicting" as const,
  };
  const changed = updateDraftValue(
    createReviewDraft([original]),
    "field-1",
    "changed",
  );
  const [restored] = updateDraftValue(changed, "field-1", "original");

  assert.ok(restored);
  assert.equal(restored.value, original.value);
  assert.equal(restored.displayValue, original.displayValue);
  assert.equal(restored.manuallyEdited, original.manuallyEdited);
  assert.equal(restored.valueSource, original.valueSource);
  assert.equal(restored.status, original.status);
  assert.equal(restored.requiresReview, original.requiresReview);
  assert.deepEqual(restored.reviewReasonCodes, original.reviewReasonCodes);
  assert.equal(isDraftDirty([original], [restored]), false);
});

test("clearing a newly added manual field recalculates its missing state", () => {
  const draft = addManualDraftField(
    createReviewDraft([fieldFixture()]),
    { dataType: "string", label: "Reference", value: "ABC" },
    "client-1",
  );

  const cleared = updateDraftValue(draft, "client-1", "");
  const clearedManual = cleared[1];

  assert.ok(clearedManual);
  assert.equal(clearedManual.value, null);
  assert.equal(clearedManual.status, "missing");
  assert.equal(clearedManual.requiresReview, false);
  assert.deepEqual(clearedManual.reviewReasonCodes, []);
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
