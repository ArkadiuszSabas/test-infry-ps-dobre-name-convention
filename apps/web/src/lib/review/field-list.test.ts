import assert from "node:assert/strict";
import test from "node:test";

import {
  matchesReviewFieldSearch,
  sortReviewFieldsByDocumentLocation,
} from "./field-list";
import type { ReviewFieldItem } from "./types";

test("sorts OCR fields by page and source order before unlocated fields", () => {
  const fields = [
    fieldFixture("manual", []),
    fieldFixture("second-page", [sourceFixture(2, 1)]),
    fieldFixture("first-page-second", [sourceFixture(1, 2)]),
    fieldFixture("first-page-first", [sourceFixture(1, 1)]),
    fieldFixture("first-page-line", [sourceFixture(1, 3, "ocr_line")]),
    fieldFixture("unlocated", [
      { ...sourceFixture(1, 0), kind: "ocr_document" },
    ]),
  ];

  assert.deepEqual(
    sortReviewFieldsByDocumentLocation(fields).map((field) => field.id),
    [
      "first-page-first",
      "first-page-second",
      "first-page-line",
      "second-page",
      "manual",
      "unlocated",
    ],
  );
});

test("searches review field labels and values without case sensitivity", () => {
  assert.equal(
    matchesReviewFieldSearch(
      fieldFixture("id", [], "Invoice number", "FV-42"),
      "invoice",
    ),
    true,
  );
  assert.equal(
    matchesReviewFieldSearch(
      fieldFixture("id", [], "Invoice number", "FV-42"),
      "fv-42",
    ),
    true,
  );
  assert.equal(
    matchesReviewFieldSearch(
      fieldFixture("id", [], "Invoice number", "FV-42"),
      "total",
    ),
    false,
  );
});

function fieldFixture(
  id: string,
  sources: ReviewFieldItem["sources"],
  label = id,
  value: string | null = "value",
): ReviewFieldItem {
  return {
    attributeExternalId: null,
    attributeId: null,
    confidence: null,
    dataType: "string",
    displayOrder: 10,
    displayValue: value,
    id,
    kind: "manual",
    label,
    manuallyEdited: false,
    required: false,
    requiresReview: false,
    reviewReasonCodes: [],
    sources,
    status: "present",
    validations: [],
    value,
    valueSource: "manual",
  };
}

function sourceFixture(
  pageNumber: number,
  orderIndex: number,
  kind: "ocr_key_value_pair" | "ocr_line" = "ocr_key_value_pair",
) {
  return {
    boundingPolygon: [],
    confidence: null,
    coordinateSystem: "normalized_0_1" as const,
    kind,
    orderIndex,
    pageNumber,
    sourceKey: null,
  };
}
