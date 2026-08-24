import assert from "node:assert/strict";
import test from "node:test";

import { validateConfidenceColorBands } from "./validation";

test("accepts one to five bands that cover 0 through 100 exactly", () => {
  const result = validateConfidenceColorBands([
    { start: 76, end: 100, color: "green" },
    { start: 0, end: 50, color: "red" },
    { start: 51, end: 75, color: "orange" },
  ]);

  assert.equal(result.valid, true);
  assert.deepEqual(result.bands, [
    { start: 0, end: 50, color: "red" },
    { start: 51, end: 75, color: "orange" },
    { start: 76, end: 100, color: "green" },
  ]);
});

test("rejects overlaps and gaps", () => {
  const overlap = validateConfidenceColorBands([
    { start: 0, end: 20, color: "red" },
    { start: 15, end: 100, color: "green" },
  ]);
  const gap = validateConfidenceColorBands([
    { start: 0, end: 20, color: "red" },
    { start: 22, end: 100, color: "green" },
  ]);

  assert.equal(overlap.valid, false);
  assert.equal(
    overlap.issues.some((issue) => issue.code === "gapOrOverlap"),
    true,
  );
  assert.equal(gap.valid, false);
  assert.equal(
    gap.issues.some((issue) => issue.code === "gapOrOverlap"),
    true,
  );
});

test("rejects missing, fractional, inverted, and out-of-range boundaries", () => {
  const result = validateConfidenceColorBands([
    { start: null, end: 10.5, color: "red" },
    { start: 101, end: 90, color: "green" },
  ]);

  assert.equal(result.valid, false);
  assert.deepEqual(
    new Set(result.issues.map((issue) => issue.code)),
    new Set([
      "boundaryRequired",
      "boundaryInteger",
      "boundaryRange",
      "invertedRange",
    ]),
  );
});

test("rejects more than five bands", () => {
  const result = validateConfidenceColorBands([
    { start: 0, end: 9, color: "red" },
    { start: 10, end: 19, color: "orange" },
    { start: 20, end: 29, color: "yellow" },
    { start: 30, end: 39, color: "green" },
    { start: 40, end: 49, color: "blue" },
    { start: 50, end: 100, color: "green" },
  ]);

  assert.equal(result.valid, false);
  assert.equal(
    result.issues.some((issue) => issue.code === "bandCount"),
    true,
  );
});
