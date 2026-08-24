import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { AttributeDefinition, DictionaryField } from "./types";
import {
  applyDictionaryFieldTypeOption,
  buildDictionaryFieldDraftRows,
  deriveDictionaryEntryLabel,
  filterAttributesByStatus,
  formatAllowedValues,
  formatDictionaryEntryInputValue,
  generateDictionaryFieldValue,
  getDictionaryEntryDisplayFields,
  getDictionaryFieldTypeOption,
  getDuplicateDictionaryFieldIds,
  getAttributeCategoryOptions,
  getAttributeFilterCount,
  getCatalogStatusFilterCount,
  getDocumentTypeMetrics,
  parseAllowedValues,
  parseDictionaryEntryValue,
  toGeneratedExternalId,
} from "./view-model";

const CONTRACT_NUMBER_ID = "22222222-2222-2222-2222-222222222222";
const GROSS_AMOUNT_ID = "33333333-3333-3333-3333-333333333333";

describe("admin settings view model", () => {
  it("maps document type counts to filter and metric values", () => {
    const meta = {
      activeCount: 3,
      inactiveCount: 2,
      returnedCount: 5,
      status: "all" as const,
      totalCount: 5,
    };

    assert.deepEqual(getDocumentTypeMetrics(meta), [
      { id: "total", value: 5 },
      { id: "active", value: 3 },
      { id: "inactive", value: 2 },
    ]);
    assert.equal(getCatalogStatusFilterCount(meta, "active"), 3);
    assert.equal(getCatalogStatusFilterCount(meta, "inactive"), 2);
    assert.equal(getCatalogStatusFilterCount(meta, "all"), 5);
  });

  it("filters attributes by lifecycle status and keeps category tabs sorted", () => {
    const attributes = [
      attributeFixture({
        externalId: "gross_amount",
        id: GROSS_AMOUNT_ID,
        status: "inactive",
      }),
      attributeFixture({
        externalId: "contract_number",
        id: CONTRACT_NUMBER_ID,
        status: "active",
      }),
    ];

    assert.deepEqual(
      filterAttributesByStatus(attributes, "active").map(
        (attribute) => attribute.id,
      ),
      [CONTRACT_NUMBER_ID],
    );
    assert.equal(getAttributeFilterCount(attributes, "all"), 2);
    assert.deepEqual(
      getAttributeCategoryOptions({
        categoryCounts: [
          { category: "Financial data", count: 1 },
          { category: "Contract data", count: 1 },
        ],
        totalCount: 2,
      }).map((category) => category.category),
      ["Contract data", "Financial data"],
    );
  });

  it("normalizes multiline and comma separated allowed values", () => {
    assert.deepEqual(parseAllowedValues("standard, annex\nstandard\n"), [
      "standard",
      "annex",
    ]);
    assert.equal(formatAllowedValues(["standard", "annex"]), "standard\nannex");
  });

  it("builds dictionary field drafts and disambiguates duplicate entry labels", () => {
    const fields = buildDictionaryFieldDraftRows([
      {
        constraints: {},
        createdAt: "2026-06-25T10:00:00Z",
        dataType: "string",
        dictionaryId: "dictionary-id",
        externalId: "code",
        format: {},
        id: "field-2",
        isUnique: true,
        label: "Code",
        normalization: {},
        required: true,
        sortOrder: 2,
        status: "active",
        updatedAt: "2026-06-25T10:00:00Z",
      },
      {
        constraints: {},
        createdAt: "2026-06-25T10:00:00Z",
        dataType: "string",
        dictionaryId: "dictionary-id",
        externalId: "region",
        format: {},
        id: "field-1",
        isUnique: false,
        label: "Region",
        normalization: {},
        required: false,
        sortOrder: 1,
        status: "active",
        updatedAt: "2026-06-25T10:00:00Z",
      },
    ]);

    assert.deepEqual(
      fields.map((field) => field.externalId),
      ["region", "code"],
    );
    assert.deepEqual(
      getDuplicateDictionaryFieldIds([
        ...fields,
        { ...fields[0]!, rowId: "duplicate" },
      ]),
      ["region"],
    );
    assert.deepEqual(
      getDictionaryEntryDisplayFields(
        {
          createdAt: "2026-06-25T10:00:00Z",
          dictionaryId: "dictionary-id",
          externalId: "finance-west",
          id: "entry-id",
          label: "Finance",
          sortOrder: 0,
          status: "active",
          updatedAt: "2026-06-25T10:00:00Z",
          values: { code: "FIN-W", region: "West" },
        },
        fields.map((field) => ({
          ...field,
          dictionaryId: "dictionary-id",
          id: field.rowId,
          createdAt: "2026-06-25T10:00:00Z",
          updatedAt: "2026-06-25T10:00:00Z",
        })),
      ),
      ["Region: West", "Code: FIN-W"],
    );
  });

  it("maps dictionary identifier presets without changing API scalar data types", () => {
    const manualUuidPreset = applyDictionaryFieldTypeOption("uuid", {
      constraints: {},
      format: {},
    });
    const uuidPreset = applyDictionaryFieldTypeOption("uuid_auto", {
      constraints: {},
      format: {},
    });
    const manualNumericPreset = applyDictionaryFieldTypeOption(
      "integer_identifier",
      {
        constraints: {},
        format: {},
      },
    );
    const numericPreset = applyDictionaryFieldTypeOption(
      "integer_identifier_auto",
      {
        constraints: {},
        format: {},
      },
    );
    const uuidField = dictionaryFieldFixture({
      dataType: uuidPreset.dataType,
      externalId: "id",
      format: uuidPreset.format,
      label: "ID",
      sortOrder: 0,
    });
    const nameField = dictionaryFieldFixture({
      externalId: "name",
      label: "Name",
      sortOrder: 1,
    });
    const numericField = dictionaryFieldFixture({
      dataType: numericPreset.dataType,
      externalId: "number_id",
      format: numericPreset.format,
      label: "Number ID",
      sortOrder: 0,
    });

    assert.equal(manualUuidPreset.dataType, "string");
    assert.deepEqual(manualUuidPreset.format, {
      generation: "manual",
      semantic_type: "uuid",
    });
    assert.equal(
      getDictionaryFieldTypeOption("string", manualUuidPreset.format),
      "uuid",
    );
    assert.equal(uuidPreset.dataType, "string");
    assert.deepEqual(uuidPreset.format, {
      generation: "auto",
      semantic_type: "uuid",
    });
    assert.equal(
      getDictionaryFieldTypeOption("string", uuidPreset.format),
      "uuid_auto",
    );
    assert.equal(manualNumericPreset.dataType, "integer");
    assert.deepEqual(manualNumericPreset.format, {
      generation: "manual",
      semantic_type: "numeric_identifier",
    });
    assert.equal(
      getDictionaryFieldTypeOption("integer", manualNumericPreset.format),
      "integer_identifier",
    );
    assert.equal(numericPreset.dataType, "integer");
    assert.deepEqual(numericPreset.format, {
      generation: "auto",
      semantic_type: "numeric_identifier",
    });
    assert.equal(
      getDictionaryFieldTypeOption("integer", numericPreset.format),
      "integer_identifier_auto",
    );
    assert.equal(generateDictionaryFieldValue(uuidField), "");
    assert.equal(generateDictionaryFieldValue(numericField), "");
    assert.equal(
      deriveDictionaryEntryLabel({
        fields: [uuidField, nameField],
        values: {
          id: "11111111-1111-1111-1111-111111111111",
          name: "Finance",
        },
      }),
      "Finance",
    );
    assert.equal(
      toGeneratedExternalId("Dzial Finansów", "entry"),
      "dzial_finansow",
    );
  });

  it("formats datetime dictionary entry values for browser controls and API payloads", () => {
    assert.equal(
      formatDictionaryEntryInputValue("2026-06-25T10:15:30+00:00", "datetime"),
      "2026-06-25T10:15",
    );
    assert.equal(
      parseDictionaryEntryValue("2026-06-25T10:15", "datetime"),
      "2026-06-25T10:15:00",
    );
  });
});

function attributeFixture(
  overrides: Partial<AttributeDefinition>,
): AttributeDefinition {
  return {
    allowedValues: [],
    category: "Contract data",
    categoryId: null,
    comment: null,
    constraints: {},
    createdAt: "2026-06-02T10:00:00Z",
    dataType: "string",
    dictionaryId: null,
    externalId: "contract_number",
    id: CONTRACT_NUMBER_ID,
    llmContext: null,
    name: "Contract number",
    schemaVersion: 1,
    source: "ai",
    status: "active",
    updatedAt: "2026-06-02T10:00:00Z",
    valueSource: "free_text",
    ...overrides,
  };
}

function dictionaryFieldFixture(
  overrides: Partial<DictionaryField>,
): DictionaryField {
  return {
    constraints: {},
    createdAt: "2026-06-25T10:00:00Z",
    dataType: "string",
    dictionaryId: "dictionary-id",
    externalId: "code",
    format: {},
    id: "field-id",
    isUnique: false,
    label: "Code",
    normalization: {},
    required: false,
    sortOrder: 0,
    status: "active",
    updatedAt: "2026-06-25T10:00:00Z",
    ...overrides,
  };
}
