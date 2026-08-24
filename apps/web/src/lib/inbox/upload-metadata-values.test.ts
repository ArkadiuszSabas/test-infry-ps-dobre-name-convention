import assert from "node:assert/strict";
import test from "node:test";

import type { ManualUploadMetadataField } from "./types";
import { buildMetadataValues } from "./upload-metadata-values";

test("upload metadata values preserve decimal number metadata", () => {
  const result = buildMetadataValues({
    fields: [
      metadataField({
        dataType: "number",
        key: "gross_amount",
        label: "Gross amount",
        required: false,
      }),
    ],
    messages: {
      integer: "Integer required",
      number: "Number required",
      required: "Required",
    },
    values: { gross_amount: "123.45" },
  });

  assert.deepEqual(result, { values: { gross_amount: 123.45 } });
});

test("upload metadata values reject decimal integer metadata", () => {
  const result = buildMetadataValues({
    fields: [
      metadataField({
        dataType: "integer",
        key: "line_count",
        label: "Line count",
        required: false,
      }),
    ],
    messages: {
      integer: "Integer required",
      number: "Number required",
      required: "Required",
    },
    values: { line_count: "123.45" },
  });

  assert.deepEqual(result, { errors: { line_count: "Integer required" } });
});

function metadataField(
  overrides: Partial<ManualUploadMetadataField>,
): ManualUploadMetadataField {
  return {
    allowedValues: [],
    category: "Metadata",
    constraints: {},
    dataType: "string",
    dictionaryId: null,
    externalId: overrides.key ?? "field",
    id: "55555555-5555-5555-5555-555555555555",
    key: "field",
    label: "Field",
    required: false,
    schemaVersion: 1,
    status: "active",
    valueSource: "free_text",
    ...overrides,
  };
}
