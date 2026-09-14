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
  getReviewFieldDisplayValuePresentations,
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

test("review field display values render OCR table evidence without its technical wrapper", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue:
        "Table 2, row 4, cells: ['Wysokość miesięcznego czynszu (suma)', '455,00 zł']; Table 2, row 10, cells: ['Opłata za monitoring urządzenia', 'Opłata miesięczna za Pakiet 15,00 zł']",
      value: "raw value remains unchanged",
    }),
    [
      "Wysokość miesięcznego czynszu (suma) · 455,00 zł",
      "Opłata za monitoring urządzenia · Opłata miesięczna za Pakiet 15,00 zł",
    ],
  );
});

test("review field display values retain text following OCR table evidence", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue:
        'Table 1, row 2, cells: ["Data rozpoczęcia okresu najmu", "Zgodnie z Protokołem Instalacji"]; Okres Najmu określony w Załączniku nr 3 do Umowy.',
      value: "raw value remains unchanged",
    }),
    [
      "Data rozpoczęcia okresu najmu · Zgodnie z Protokołem Instalacji",
      "Okres Najmu określony w Załączniku nr 3 do Umowy.",
    ],
  );
});

test("review field display values use structured table rows before the legacy separator fallback", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: "1 | Prepare annex | 100 zł\n2 | Next annex | 50 zł",
      value: "raw value",
      presentationRows: [
        ["1", "Prepare annex", "100 zł"],
        ["2", "Next annex", "50 zł"],
      ],
    }),
    ["1 · Prepare annex · 100 zł", "2 · Next annex · 50 zł"],
  );
});

test("review field display values use matching table rows for semicolon-separated aggregates", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: "455,00 zł; 15,00 zł",
      value: "raw value",
      presentationRows: [["455,00 zł"], ["15,00 zł"]],
    }),
    ["455,00 zł", "15,00 zł"],
  );
});

test("review field display values retain numbering metadata from table rows", () => {
  assert.deepEqual(
    getReviewFieldDisplayValuePresentations({
      displayValue: "1 | Prepare annex | 100 zł",
      value: "raw value",
      presentationRows: [["1", "Prepare annex", "100 zł"]],
    }),
    [{ value: "1 · Prepare annex · 100 zł", isNumbered: true }],
  );
});

test("review field display values retain numbering metadata after structural rows merge", () => {
  assert.deepEqual(
    getReviewFieldDisplayValuePresentations({
      displayValue: "1 | 4) Czynsz | Uwagi | 2 | Aneks",
      value: "raw value",
      presentationRows: [["1"], ["4) Czynsz"], ["Uwagi"], ["2", "Aneks"]],
    }),
    [
      { value: "14) Czynsz", isNumbered: true },
      { value: "Uwagi", isNumbered: false },
      { value: "2 · Aneks", isNumbered: true },
    ],
  );
});

test("review field display values keep display text when table evidence includes extra cells", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: "Opłata za monitoring | 15,00 zł",
      value: "raw value",
      presentationRows: [["Opłata za monitoring", "15,00 zł", "455,00 zł"]],
    }),
    ["Opłata za monitoring", "15,00 zł"],
  );
});

test("review field display values keep scalar values instead of unrelated table evidence", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: "Nolato Stargard Sp. z o.o.",
      value: "Nolato Stargard Sp. z o.o.",
      presentationRows: [["Firma", "Nolato Stargard Sp. z o.o."]],
    }),
    ["Nolato Stargard Sp. z o.o."],
  );
});

test("review field display values format OCR selection marks without changing the source", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: ":unselected: :selected: :unselected:",
      value: "raw value",
    }),
    ["☐ ☑ ☐"],
  );
});

test("review field display values coalesce a section marker with its repeated heading number", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: "§ | 1 | 1. ROZWIĄZANIE UMOWY",
      value: "raw value",
      presentationRows: [["§"], ["1"], ["1. ROZWIĄZANIE UMOWY"]],
    }),
    ["§ 1. ROZWIĄZANIE UMOWY"],
  );
});

test("review field display values join a two-digit point number split between table rows", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: "1 | 4) Czynsz, opłata za Wydruki oraz Skany",
      value: "raw value",
      presentationRows: [["1"], ["4) Czynsz, opłata za Wydruki oraz Skany"]],
    }),
    ["14) Czynsz, opłata za Wydruki oraz Skany"],
  );
});

test("review field display values join a two-digit point number split by a legacy separator", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue:
        "2 | 1) Tonery dostarczane będą w ilości adekwatnej do rzeczywistego zużycia",
      value: "raw value",
    }),
    [
      "21) Tonery dostarczane będą w ilości adekwatnej do rzeczywistego zużycia",
    ],
  );
});

test("review field display values split newline and numbered values", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: "1. First item\n2) Second item",
      value: "raw value",
    }),
    ["1. First item", "2) Second item"],
  );
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: "1. First | 2) Second\n3. Third",
      value: "raw value",
    }),
    ["1. First", "2) Second", "3. Third"],
  );
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: "11) Pozycja | 22) Kolejna pozycja",
      value: "raw value",
    }),
    ["11) Pozycja", "22) Kolejna pozycja"],
  );
});

test("review field display values move a trailing next-item number to the next cell", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue:
        "100 zł; 2 | Przygotowanie kolejnego Aneksu | 100 zł; 3 | Następna pozycja",
      value: "raw value",
    }),
    [
      "100 zł",
      "2 Przygotowanie kolejnego Aneksu",
      "100 zł",
      "3 Następna pozycja",
    ],
  );
});

test("review field display values retain each pending number in a repeated aggregate", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: "100 zł; 2 | 200 zł; 3 | Aneks",
      value: "raw value",
    }),
    ["100 zł", "2 200 zł", "3 Aneks"],
  );
});

test("review field display values retain an unmatched trailing number", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({
      displayValue: "Okres: 2025; 2026",
      value: "raw value",
    }),
    ["Okres: 2025; 2026"],
  );
});

test("review field display values preserve single, empty, and separator-only values", () => {
  assert.deepEqual(
    getReviewFieldDisplayValues({ displayValue: "single value", value: "raw" }),
    ["single value"],
  );
  assert.deepEqual(
    getReviewFieldDisplayValues({ displayValue: "", value: "raw" }),
    [],
  );
  assert.deepEqual(
    getReviewFieldDisplayValues({ displayValue: "|| \n|", value: "raw" }),
    [],
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

test("approval blockers contain only block-approval missing required fields", () => {
  assert.deepEqual(
    getBlockingRequiredFieldIds([
      {
        id: "required-blocking",
        required: true,
        reviewReasonCodes: ["MISSING_REQUIRED_BLOCK_APPROVAL"],
        value: null,
      },
      {
        id: "required-review",
        required: true,
        reviewReasonCodes: ["MISSING_REQUIRED_REVIEW"],
        value: null,
      },
      {
        id: "required-legacy",
        required: true,
        reviewReasonCodes: ["MISSING_REQUIRED_VALUE"],
        value: null,
      },
      {
        id: "required-unknown-policy",
        required: true,
        reviewReasonCodes: [],
        value: null,
      },
      {
        id: "required-blank",
        required: true,
        reviewReasonCodes: ["MISSING_REQUIRED_BLOCK_APPROVAL"],
        value: "  ",
      },
      {
        id: "required-present",
        required: true,
        reviewReasonCodes: ["MISSING_REQUIRED_BLOCK_APPROVAL"],
        value: "value",
      },
      {
        id: "optional-missing",
        required: false,
        reviewReasonCodes: ["MISSING_REQUIRED_BLOCK_APPROVAL"],
        value: null,
      },
    ]),
    [
      "required-blocking",
      "required-legacy",
      "required-unknown-policy",
      "required-blank",
    ],
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
