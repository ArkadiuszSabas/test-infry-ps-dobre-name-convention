import assert from "node:assert/strict";
import test from "node:test";

import type {
  DictionaryLookupEntry,
  DocumentMetadataSchemaField,
} from "./types";
import {
  buildDocumentParameterSections,
  formatFileSize,
  getActiveDocumentTypeId,
  getDocumentTypeFilterOptions,
  getInboxDocumentStatus,
  getInboxPreviewState,
  getManualUploadDictionaryIds,
  getUploadDocumentTypeOptions,
} from "./view-model";

test("inbox status exposes a failed latest OCR run", () => {
  assert.equal(
    getInboxDocumentStatus("waiting_for_review", "failed"),
    "failed",
  );
  assert.equal(
    getInboxDocumentStatus("waiting_for_review", "running"),
    "waiting_for_review",
  );
});

test("file size formatter uses compact byte units", () => {
  const formatNumber = (value: number, options?: Intl.NumberFormatOptions) =>
    new Intl.NumberFormat("en-US", options).format(value);

  assert.equal(formatFileSize(512, formatNumber), "512 B");
  assert.equal(formatFileSize(1536, formatNumber), "1.5 KB");
  assert.equal(formatFileSize(2 * 1024 * 1024, formatNumber), "2 MB");
  assert.equal(formatFileSize(null, formatNumber, "Unknown"), "Unknown");
});

test("preview state exposes inline PDF URLs when available", () => {
  assert.deepEqual(getInboxPreviewState("blob:http://127.0.0.1/file"), {
    kind: "available",
    url: "blob:http://127.0.0.1/file",
  });
  assert.deepEqual(getInboxPreviewState(null), { kind: "unavailable" });
  assert.deepEqual(getInboxPreviewState(undefined), { kind: "unavailable" });
});

test("document type filters reuse configured display options", () => {
  const options = getDocumentTypeFilterOptions({
    documentTypeFilters: [
      { id: "type-1", name: "Type 1" },
      { id: "type-2", name: "Type 2" },
    ],
    documentTypes: [
      {
        displayLabel: "Type 1 - Finance",
        id: "type-1",
        name: "Type 1",
        parameters: [{ code: "pion", label: "Pion", value: "Finance" }],
      },
    ],
  });

  assert.deepEqual(options, [
    {
      displayLabel: "Type 1 - Finance",
      id: "type-1",
      name: "Type 1",
      parameters: [{ code: "pion", label: "Pion", value: "Finance" }],
    },
    {
      id: "type-2",
      label: "Type 2",
      parameters: [],
    },
  ]);
});

test("upload document type options follow manual upload availability", () => {
  assert.deepEqual(
    getUploadDocumentTypeOptions({
      manualUploadDocumentTypes: [
        { externalId: "type_a", id: "type-a", name: "Type A" },
        { externalId: "type_b", id: "type-b", name: "Type B" },
      ],
      systemCatalogOptions: [
        {
          displayLabel: "Type A - Finance",
          id: "type-a",
          name: "Type A",
          parameters: [{ code: "pion", label: "Pion", value: "Finance" }],
        },
      ],
    }).map((option) => option.id),
    ["type-a", "type-b"],
  );
  assert.deepEqual(
    getUploadDocumentTypeOptions({
      manualUploadDocumentTypes: [
        { externalId: "type_a", id: "type-a", name: "Type A" },
      ],
      systemCatalogOptions: [
        {
          displayLabel: "Type A - Finance",
          id: "type-a",
          name: "Type A",
          parameters: [{ code: "pion", label: "Pion", value: "Finance" }],
        },
      ],
    })[0]?.displayLabel,
    "Type A - Finance",
  );
});

test("active document type id falls back to the first option", () => {
  assert.equal(
    getActiveDocumentTypeId({
      options: [
        { id: "first", label: "First" },
        { id: "second", label: "Second" },
      ],
      selectedDocumentTypeId: "missing",
    }),
    "first",
  );
  assert.equal(
    getActiveDocumentTypeId({
      options: [{ id: "second", label: "Second" }],
      selectedDocumentTypeId: "second",
    }),
    "second",
  );
});

test("manual upload dictionary ids are deduplicated", () => {
  assert.deepEqual(
    getManualUploadDictionaryIds([
      metadataField({ dictionaryId: "dict-1" }),
      metadataField({ dictionaryId: null }),
      metadataField({ dictionaryId: "dict-1" }),
      metadataField({ dictionaryId: "dict-2" }),
    ]),
    ["dict-1", "dict-2"],
  );
});

test("document parameters list required fields before optional fields", () => {
  const sections = buildDocumentParameterSections({
    fields: [
      metadataField({
        key: "counterparty",
        label: "Counterparty",
        required: false,
      }),
      metadataField({
        key: "contract_number",
        label: "Contract number",
        required: true,
      }),
    ],
    values: { contract_number: "A/1" },
  });

  assert.deepEqual(
    sections.map((section) => section.requirement),
    ["required", "optional"],
  );
  assert.equal(sections[0]?.items[0]?.field.key, "contract_number");
  assert.equal(sections[1]?.items[0]?.field.key, "counterparty");
  assert.equal(sections[1]?.items[0]?.missing, true);
});

test("document parameters expose dictionary fields as select options", () => {
  const dictionaryId = "77777777-7777-7777-7777-777777777777";
  const sections = buildDocumentParameterSections({
    dictionaryOptionsById: new Map([
      [
        dictionaryId,
        [
          dictionaryEntry({
            externalId: "pl",
            label: "Poland",
            sortOrder: 1,
          }),
          dictionaryEntry({
            externalId: "de",
            label: "Germany",
            sortOrder: 0,
          }),
        ],
      ],
    ]),
    fields: [
      metadataField({
        dictionaryId,
        key: "country",
        label: "Country",
        valueSource: "dictionary",
      }),
    ],
    values: { country: "pl" },
  });

  const item = sections[0]?.items[0];
  assert.equal(item?.controlKind, "select");
  assert.equal(item?.selectedOptionLabel, "Poland");
  assert.deepEqual(
    item?.options.map((option) => option.value),
    ["de", "pl"],
  );
});

test("document parameters mark UUID-like string fields by constraints", () => {
  const sections = buildDocumentParameterSections({
    fields: [
      metadataField({
        constraints: {
          pattern:
            "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        },
        key: "source_id",
        label: "Source ID",
      }),
    ],
    values: { source_id: "33333333-3333-3333-3333-333333333333" },
  });

  assert.equal(sections[0]?.items[0]?.typeKind, "uuid");
  assert.equal(sections[0]?.items[0]?.controlKind, "text");
});

function metadataField(
  overrides: Partial<DocumentMetadataSchemaField>,
): DocumentMetadataSchemaField {
  return {
    allowedValues: [],
    category: "Contract data",
    constraints: {},
    createdAt: "2026-06-05T10:00:00Z",
    dataType: "string",
    dictionaryId: null,
    externalId: overrides.key ?? "field",
    id: "55555555-5555-5555-5555-555555555555",
    key: "field",
    label: "Field",
    required: true,
    schemaVersion: 1,
    status: "active",
    updatedAt: "2026-06-05T10:00:00Z",
    valueSource: "free_text",
    ...overrides,
  };
}

function dictionaryEntry(
  overrides: Partial<DictionaryLookupEntry>,
): DictionaryLookupEntry {
  return {
    createdAt: "2026-06-25T10:00:00Z",
    dictionaryId: "77777777-7777-7777-7777-777777777777",
    externalId: "entry",
    id: "88888888-8888-8888-8888-888888888888",
    label: "Entry",
    sortOrder: null,
    status: "active",
    updatedAt: "2026-06-25T10:00:00Z",
    values: {},
    ...overrides,
  };
}
