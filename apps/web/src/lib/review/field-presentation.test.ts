import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  KNOWN_REVIEW_REASON_CODES,
  REVIEW_REASON_BADGE_VARIANTS,
  REVIEW_REASON_POPUP_KEYS,
  getBlockingRequiredFieldIds,
  getDisplayedConfidencePercent,
  getReviewFieldDisplayValues,
  getReviewReasonCodeLabels,
  getReviewReasonCodePresentations,
} from "./field-presentation";

test("review field display values split pipe-delimited values without changing the source text", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({ displayValue: "A | B | C", value: "A|B|C" }),
    ["A", "B", "C"],
  );
  assert.deepEqual(
    getReviewFieldDisplayValues({ displayValue: null, value: "single value" }),
    ["single value"],
  );
  assert.deepEqual(
    getReviewFieldDisplayValues({ displayValue: "A|| C ", value: "ignored" }),
    ["A", "C"],
  );
});

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

test("review reason codes suppress redundant badges and preserve unknown backend codes", () => {
  assert.deepEqual(
    getReviewReasonCodeLabels([], (code) => `translated:${code}`),
    [],
  );
  assert.deepEqual(
    getReviewReasonCodeLabels(
      ["LOW_CONFIDENCE", "FUTURE_BACKEND_REASON"],
      (code) => `translated:${code}`,
    ),
    ["FUTURE_BACKEND_REASON"],
  );
  assert.deepEqual(
    getReviewReasonCodeLabels(
      [
        "LOW_CONFIDENCE",
        "MISSING_REQUIRED_BLOCK_APPROVAL",
        "MISSING_REQUIRED_REVIEW",
        "MISSING_REQUIRED_VALUE",
        "MISSING_VALUE",
        "MANUAL_INPUT_REQUIRED",
        "KV_CONSISTENCY_CONFLICT",
      ],
      (code) => `translated:${code}`,
    ),
    [],
  );
});

test("rendered review reasons use audience tones and muted configuration variants", () => {
  const presentations = getReviewReasonCodePresentations(
    [
      "METADATA_CONTRADICTED",
      "CONFLICTING_VALUES",
      "EVIDENCE_QUOTE_NOT_FOUND",
      "VALUE_NOT_DERIVABLE",
      "VALUE_TYPE_MISMATCH",
      "VALUE_OUTSIDE_DICTIONARY",
      "EVIDENCE_TOO_SCATTERED",
      "FIELD_NOT_PROCESSED",
      "MODEL_OUTPUT_INVALID",
      "ATTRIBUTE_CONSTRAINT_REJECTED",
      "ATTRIBUTE_CONSTRAINT_UNSATISFIABLE",
      "ATTRIBUTE_MAPPING_MISSING",
      "FUTURE_BACKEND_REASON",
    ],
    (code) => `translated:${code}`,
  );

  assert.deepEqual(
    presentations.map(({ code, popupKey, tone }) => [code, popupKey, tone]),
    [
      ["METADATA_CONTRADICTED", "METADATA_CONTRADICTED", "decision"],
      ["CONFLICTING_VALUES", "CONFLICTING_VALUES", "decision"],
      ["EVIDENCE_QUOTE_NOT_FOUND", "EVIDENCE_QUOTE_NOT_FOUND", "decision"],
      ["VALUE_NOT_DERIVABLE", "VALUE_NOT_DERIVABLE", "decision"],
      ["VALUE_TYPE_MISMATCH", "VALUE_TYPE_MISMATCH", "decision"],
      ["VALUE_OUTSIDE_DICTIONARY", "VALUE_OUTSIDE_DICTIONARY", "decision"],
      ["EVIDENCE_TOO_SCATTERED", "EVIDENCE_TOO_SCATTERED", "decision"],
      ["FIELD_NOT_PROCESSED", "FIELD_NOT_PROCESSED", "decision"],
      ["MODEL_OUTPUT_INVALID", "MODEL_OUTPUT_INVALID", "decision"],
      [
        "ATTRIBUTE_CONSTRAINT_REJECTED",
        "ATTRIBUTE_CONSTRAINT",
        "configuration",
      ],
      [
        "ATTRIBUTE_CONSTRAINT_UNSATISFIABLE",
        "ATTRIBUTE_CONSTRAINT",
        "configuration",
      ],
      [
        "ATTRIBUTE_MAPPING_MISSING",
        "ATTRIBUTE_MAPPING_MISSING",
        "configuration",
      ],
      ["FUTURE_BACKEND_REASON", "MODEL_OUTPUT_INVALID", "decision"],
    ],
  );
  assert.deepEqual(REVIEW_REASON_BADGE_VARIANTS, {
    configuration: "outline",
    decision: "outline",
    informational: "secondary",
  });
});

test("source-system reason is informational and precedes metadata review reasons", () => {
  assert.deepEqual(
    getReviewReasonCodePresentations(
      ["VALUE_FROM_SOURCE_SYSTEM"],
      (code) => code,
    ).map(({ code }) => code),
    ["VALUE_FROM_SOURCE_SYSTEM"],
  );
  assert.deepEqual(
    getReviewReasonCodePresentations(
      ["VALUE_FROM_SOURCE_SYSTEM", "METADATA_NOT_CONFIRMED"],
      (code) => code,
    ).map(({ code, popupKey, tone }) => [code, popupKey, tone]),
    [["VALUE_FROM_SOURCE_SYSTEM", "VALUE_FROM_SOURCE_SYSTEM", "informational"]],
  );
  assert.deepEqual(
    getReviewReasonCodePresentations(
      ["VALUE_FROM_SOURCE_SYSTEM", "METADATA_CONTRADICTED"],
      (code) => code,
    ).map(({ code }) => code),
    ["VALUE_FROM_SOURCE_SYSTEM", "METADATA_CONTRADICTED"],
  );
});

test("Polish and English messages cover every review reason label and popup", () => {
  const messageDirectory = fileURLToPath(
    new URL("../../messages/", import.meta.url),
  );
  const localeMessages = [];
  for (const locale of ["pl", "en"]) {
    const messages = JSON.parse(
      readFileSync(`${messageDirectory}${locale}.json`, "utf8"),
    ) as {
      ReviewWorkspace: {
        fields: {
          reasonCodes: Record<string, string>;
          reasonPopup: {
            codes: Record<
              string,
              { action: string; happened: string; meaning: string }
            >;
          };
        };
      };
    };
    localeMessages.push(messages.ReviewWorkspace.fields);
    assert.deepEqual(
      Object.keys(messages.ReviewWorkspace.fields.reasonCodes).sort(),
      [...KNOWN_REVIEW_REASON_CODES].sort(),
    );
    assert.deepEqual(
      Object.keys(messages.ReviewWorkspace.fields.reasonPopup.codes).sort(),
      [...new Set(Object.values(REVIEW_REASON_POPUP_KEYS))].sort(),
    );
    for (const content of Object.values(
      messages.ReviewWorkspace.fields.reasonPopup.codes,
    )) {
      assert.deepEqual(Object.keys(content).sort(), [
        "action",
        "happened",
        "meaning",
      ]);
    }
  }
  assert.deepEqual(
    Object.keys(localeMessages[0].reasonCodes).sort(),
    Object.keys(localeMessages[1].reasonCodes).sort(),
  );
  assert.deepEqual(
    Object.keys(localeMessages[0].reasonPopup.codes).sort(),
    Object.keys(localeMessages[1].reasonPopup.codes).sort(),
  );
});
