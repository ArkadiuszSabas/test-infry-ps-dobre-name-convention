import assert from "node:assert/strict";
import test from "node:test";

import {
  getBlockingRequiredFieldIds,
  getDisplayedConfidencePercent,
} from "./field-presentation";

test("missing required fields use a view-only zero confidence score", () => {
  assert.equal(
    getDisplayedConfidencePercent({
      confidence: null,
      required: true,
      value: null,
    }),
    0,
  );
  assert.equal(
    getDisplayedConfidencePercent({
      confidence: null,
      required: false,
      value: null,
    }),
    null,
  );
  assert.equal(
    getDisplayedConfidencePercent({
      confidence: null,
      required: true,
      value: "manually supplied",
    }),
    null,
  );
  assert.equal(
    getDisplayedConfidencePercent({
      confidence: 0.756,
      required: true,
      value: "extracted",
    }),
    76,
  );
});

test("approval blockers contain only missing required field identifiers", () => {
  assert.deepEqual(
    getBlockingRequiredFieldIds([
      { id: "required-missing", required: true, value: null },
      { id: "required-blank", required: true, value: "  " },
      { id: "required-present", required: true, value: "value" },
      { id: "optional-missing", required: false, value: null },
    ]),
    ["required-missing", "required-blank"],
  );
});
