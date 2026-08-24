import assert from "node:assert/strict";
import test from "node:test";

import { confidenceColorClassName, getConfidenceColor } from "./presentation";
import { DEFAULT_CONFIDENCE_COLOR_BANDS } from "./types";

test("uses inclusive configured confidence bands at their boundaries", () => {
  assert.equal(getConfidenceColor(0, DEFAULT_CONFIDENCE_COLOR_BANDS), "red");
  assert.equal(getConfidenceColor(50, DEFAULT_CONFIDENCE_COLOR_BANDS), "red");
  assert.equal(
    getConfidenceColor(51, DEFAULT_CONFIDENCE_COLOR_BANDS),
    "orange",
  );
  assert.equal(
    getConfidenceColor(75, DEFAULT_CONFIDENCE_COLOR_BANDS),
    "orange",
  );
  assert.equal(getConfidenceColor(76, DEFAULT_CONFIDENCE_COLOR_BANDS), "green");
  assert.equal(
    getConfidenceColor(100, DEFAULT_CONFIDENCE_COLOR_BANDS),
    "green",
  );
});

test("uses saved custom bands instead of hardcoded thresholds", () => {
  const bands = [
    { start: 0, end: 90, color: "blue" as const },
    { start: 91, end: 100, color: "yellow" as const },
  ];

  assert.equal(getConfidenceColor(80, bands), "blue");
  assert.equal(getConfidenceColor(95, bands), "yellow");
  assert.match(confidenceColorClassName("blue"), /bg-blue-50/);
});

test("falls back safely when a malformed runtime configuration has a gap", () => {
  assert.equal(
    getConfidenceColor(75, [{ start: 0, end: 20, color: "blue" }]),
    "orange",
  );
});
