import assert from "node:assert/strict";
import test from "node:test";

import {
  getLocatableReviewSources,
  getReviewFieldLocatableSources,
} from "./source-location";
import type { ReviewAttributeSource, ReviewFieldItem } from "./types";

const source = (
  pageNumber: number,
  orderIndex: number,
  boundingPolygon: number[] | null = [0.1, 0.1, 0.2, 0.1, 0.2, 0.2, 0.1, 0.2],
): ReviewAttributeSource => ({
  boundingPolygon,
  confidence: null,
  coordinateSystem: "normalized_0_1",
  kind: "ocr_line",
  orderIndex,
  pageNumber,
  sourceKey: null,
});

test("keeps only usable sources in a stable page and source order", () => {
  const firstOnPageTwo = source(2, 0);
  const secondOnPageTwo = source(2, 0);
  const sources = getLocatableReviewSources([
    source(3, 0),
    secondOnPageTwo,
    source(0, 0),
    source(2, 1),
    firstOnPageTwo,
    source(1, 0, null),
  ]);

  assert.deepEqual(sources, [
    secondOnPageTwo,
    firstOnPageTwo,
    source(2, 1),
    source(3, 0),
  ]);
});

test("does not offer a PDF location for manual review values", () => {
  const field = {
    kind: "manual",
    manuallyEdited: false,
    sources: [source(1, 0)],
  } as Pick<ReviewFieldItem, "kind" | "manuallyEdited" | "sources">;

  assert.deepEqual(getReviewFieldLocatableSources(field), []);
  assert.deepEqual(
    getReviewFieldLocatableSources({
      ...field,
      kind: "configured",
      manuallyEdited: true,
    }),
    [],
  );
});
test("accepts fragment OCR kinds and rejects document-level OCR", () => {
  assert.equal(
    getLocatableReviewSources([
      source(1, 0),
      { ...source(1, 1), kind: "ocr_selection_mark" },
      { ...source(1, 2), kind: "ocr_table_cell" },
      { ...source(1, 3), kind: "ocr_document" },
    ]).length,
    3,
  );
});

test("rejects malformed and unsupported source locations", () => {
  const valid = source(1, 0);
  for (const invalid of [
    { ...valid, boundingPolygon: null },
    { ...valid, boundingPolygon: [0, 0, 1] },
    {
      ...valid,
      boundingPolygon: [0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
    {
      ...valid,
      boundingPolygon: [0, 0, 1, 0, 1, 1, 0, 1].map((value, index) =>
        index === 0 ? -1 : value,
      ),
    },
    { ...valid, pageNumber: 0 },
    { ...valid, coordinateSystem: "future_coordinates" as never },
    { ...valid, orderIndex: -1 },
    { ...valid, pageNumber: 1.5 },
    { ...valid, boundingPolygon: [0, 0, 1, 0, 1, 1, 0, 1, Infinity, 0] },
    {
      ...valid,
      boundingPolygon: [0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    },
  ]) {
    assert.deepEqual(getLocatableReviewSources([invalid]), []);
  }
});
test("preserves all usable points in a multi-point polygon", () => {
  const multiPoint = source(
    2,
    0,
    [0.1, 0.1, 0.5, 0.05, 0.9, 0.1, 0.8, 0.5, 0.9, 0.9, 0.5, 0.8],
  );
  assert.deepEqual(getLocatableReviewSources([multiPoint]), [multiPoint]);
});
