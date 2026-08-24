import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { DocumentTypeDefinition, SystemCatalogDefinition } from "./types";
import {
  buildDocumentTypeExtensionDraftValues,
  buildSystemCatalogDefinitionDraft,
  filterDocumentTypesByParameterFilters,
  getDocumentTypeParameterFilters,
  getSystemCatalogExtensionDictionaryIds,
  getMissingRequiredDocumentTypeExtensionFieldIds,
  hasActiveDocumentTypeParameterFilters,
  hasDocumentTypeExtensionDraftChanges,
  normalizeDocumentTypeParameterFilterValues,
  sortSystemCatalogOptions,
  toDocumentTypeExtensionValueInput,
  toSaveSystemCatalogDefinitionInput,
} from "./system-catalog-view-model";

const DOCUMENT_TYPE_ID = "11111111-1111-1111-1111-111111111111";
const PION_FIELD_ID = "22222222-2222-2222-2222-222222222222";
const NUMBER_FIELD_ID = "33333333-3333-3333-3333-333333333333";
const DISPLAY_MODE_ID = "44444444-4444-4444-4444-444444444444";
const DICTIONARY_ID = "55555555-5555-5555-5555-555555555555";
const DICTIONARY_ENTRY_ID = "66666666-6666-6666-6666-666666666666";

describe("system catalog view model", () => {
  it("builds definition drafts and saves new display parts by field code", () => {
    const draft = buildSystemCatalogDefinitionDraft(definitionFixture());
    draft.fields.push({
      code: "numer_wewnetrzny",
      dictionaryId: null,
      isActive: true,
      isRequired: false,
      label: "Numer wewnętrzny",
      mappedAttributeDefinitionId: null,
      rowId: "new-number-field",
      showInOverview: true,
      valueType: "text",
    });
    draft.displayModes[0]?.parts.push({
      extensionFieldRowId: "new-number-field",
      rowId: "new-number-part",
      separatorBefore: " / ",
      sourceType: "extension_field",
    });

    const input = toSaveSystemCatalogDefinitionInput(draft);

    assert.equal(input.fields[1]?.code, "numer_wewnetrzny");
    assert.equal(input.fields[1]?.fieldOrder, 1);
    assert.deepEqual(input.displayModes[0]?.parts[2], {
      extensionFieldCode: "numer_wewnetrzny",
      partOrder: 2,
      separatorBefore: " / ",
      sourceType: "extension_field",
    });
  });

  it("builds document type extension payloads and required validation", () => {
    const definition = definitionFixture();
    const documentType = documentTypeFixture();
    const values = buildDocumentTypeExtensionDraftValues(documentType);

    assert.deepEqual(values, {
      [NUMBER_FIELD_ID]: "ABC/1",
      [PION_FIELD_ID]: DICTIONARY_ENTRY_ID,
    });
    assert.deepEqual(
      getMissingRequiredDocumentTypeExtensionFieldIds(definition.fields, {}),
      [PION_FIELD_ID],
    );
    assert.deepEqual(
      toDocumentTypeExtensionValueInput(definition.fields, values),
      [
        {
          dictionaryEntryId: DICTIONARY_ENTRY_ID,
          extensionFieldId: PION_FIELD_ID,
        },
        {
          extensionFieldId: NUMBER_FIELD_ID,
          textValue: "ABC/1",
        },
      ],
    );
  });

  it("detects changed document type extension draft values", () => {
    const definition = definitionFixture();
    const values = buildDocumentTypeExtensionDraftValues(documentTypeFixture());

    assert.equal(
      hasDocumentTypeExtensionDraftChanges(definition.fields, values, {
        ...values,
      }),
      false,
    );
    assert.equal(
      hasDocumentTypeExtensionDraftChanges(definition.fields, values, {
        ...values,
        [NUMBER_FIELD_ID]: "",
      }),
      true,
    );
  });

  it("sorts system catalog options by current backend label", () => {
    assert.deepEqual(
      sortSystemCatalogOptions([
        {
          displayModeId: null,
          extensionValues: [],
          id: "b",
          label: "Typ B",
          name: "Typ B",
          parameters: [],
        },
        {
          displayModeId: null,
          extensionValues: [],
          id: "a",
          label: "Typ A",
          name: "Typ A",
          parameters: [],
        },
      ]).map((option) => option.id),
      ["a", "b"],
    );
  });

  it("builds document type parameter filters from overview parameters", () => {
    const first = documentTypeFixture();
    const second = {
      ...documentTypeFixture(),
      displayLabel: "Supplier invoice - Legal",
      id: "77777777-7777-7777-7777-777777777777",
      parameters: [
        { code: "pion", label: "Pion", value: "Legal" },
        { code: "numer_wewnetrzny", label: "Numer wewnętrzny", value: null },
      ],
    } satisfies DocumentTypeDefinition;
    const third = {
      ...documentTypeFixture(),
      displayLabel: "Contract - Finance",
      id: "88888888-8888-8888-8888-888888888888",
      parameters: [
        { code: "pion", label: "Pion", value: "Finance" },
        { code: "numer_wewnetrzny", label: "Numer wewnętrzny", value: "ABC/2" },
      ],
    } satisfies DocumentTypeDefinition;

    assert.deepEqual(getDocumentTypeParameterFilters([first, second, third]), [
      {
        code: "numer_wewnetrzny",
        label: "Numer wewnętrzny",
        options: [
          { count: 1, value: "ABC/1" },
          { count: 1, value: "ABC/2" },
        ],
      },
      {
        code: "pion",
        label: "Pion",
        options: [
          { count: 2, value: "Finance" },
          { count: 1, value: "Legal" },
        ],
      },
    ]);
  });

  it("filters document types by selected parameter values", () => {
    const finance = documentTypeFixture();
    const legal = {
      ...documentTypeFixture(),
      displayLabel: "Supplier invoice - Legal",
      id: "77777777-7777-7777-7777-777777777777",
      parameters: [
        { code: "pion", label: "Pion", value: "Legal" },
        { code: "numer_wewnetrzny", label: "Numer wewnętrzny", value: "ABC/2" },
      ],
    } satisfies DocumentTypeDefinition;

    assert.deepEqual(
      filterDocumentTypesByParameterFilters([finance, legal], {
        numer_wewnetrzny: null,
        pion: "Legal",
      }).map((documentType) => documentType.id),
      [legal.id],
    );
  });

  it("normalizes parameter filter values against available options", () => {
    const filters = [
      {
        code: "pion",
        label: "Pion",
        options: [{ count: 1, value: "Finance" }],
      },
      {
        code: "region",
        label: "Region",
        options: [{ count: 1, value: "West" }],
      },
    ];

    const normalized = normalizeDocumentTypeParameterFilterValues(filters, {
      ignored: "value",
      pion: "Finance",
      region: "Removed",
    });

    assert.deepEqual(normalized, {
      pion: "Finance",
      region: null,
    });
    assert.equal(hasActiveDocumentTypeParameterFilters(normalized), true);
    assert.equal(
      hasActiveDocumentTypeParameterFilters({ pion: null, region: null }),
      false,
    );
  });

  it("deduplicates extension dictionary ids", () => {
    const fields = definitionFixture().fields;

    assert.deepEqual(getSystemCatalogExtensionDictionaryIds(fields), [
      DICTIONARY_ID,
    ]);
  });
});

function definitionFixture(): SystemCatalogDefinition {
  return {
    displayModes: [
      {
        createdAt: "2026-07-03T10:00:00Z",
        id: DISPLAY_MODE_ID,
        isActive: true,
        isDefault: true,
        name: "Typ - Pion",
        parts: [
          {
            displayModeId: DISPLAY_MODE_ID,
            extensionFieldId: null,
            id: "part-base",
            partOrder: 0,
            separatorBefore: null,
            sourceType: "base_name",
          },
          {
            displayModeId: DISPLAY_MODE_ID,
            extensionFieldId: PION_FIELD_ID,
            id: "part-pion",
            partOrder: 1,
            separatorBefore: " - ",
            sourceType: "extension_field",
          },
        ],
        systemCatalogKey: "document_type",
        updatedAt: "2026-07-03T10:00:00Z",
      },
    ],
    fields: [
      {
        code: "pion",
        createdAt: "2026-07-03T10:00:00Z",
        dictionaryId: DICTIONARY_ID,
        fieldOrder: 0,
        id: PION_FIELD_ID,
        isActive: true,
        isRequired: true,
        label: "Pion",
        mappedAttributeDefinitionId: null,
        showInOverview: true,
        systemCatalogKey: "document_type",
        updatedAt: "2026-07-03T10:00:00Z",
        valueType: "dictionary",
      },
      {
        code: "numer_wewnetrzny",
        createdAt: "2026-07-03T10:00:00Z",
        dictionaryId: null,
        fieldOrder: 1,
        id: NUMBER_FIELD_ID,
        isActive: true,
        isRequired: false,
        label: "Numer wewnętrzny",
        mappedAttributeDefinitionId: null,
        showInOverview: true,
        systemCatalogKey: "document_type",
        updatedAt: "2026-07-03T10:00:00Z",
        valueType: "text",
      },
    ],
    systemCatalogKey: "document_type",
  };
}

function documentTypeFixture(): DocumentTypeDefinition {
  return {
    createdAt: "2026-07-03T10:00:00Z",
    description: null,
    displayLabel: "Supplier invoice - Finance",
    displayModeId: DISPLAY_MODE_ID,
    extensionValues: [
      {
        code: "pion",
        dictionaryEntryId: DICTIONARY_ENTRY_ID,
        dictionaryId: DICTIONARY_ID,
        displayValue: "Finance",
        extensionFieldId: PION_FIELD_ID,
        fieldOrder: 0,
        label: "Pion",
        showInOverview: true,
        textValue: null,
        valueType: "dictionary",
      },
      {
        code: "numer_wewnetrzny",
        dictionaryEntryId: null,
        dictionaryId: null,
        displayValue: "ABC/1",
        extensionFieldId: NUMBER_FIELD_ID,
        fieldOrder: 1,
        label: "Numer wewnętrzny",
        showInOverview: true,
        textValue: "ABC/1",
        valueType: "text",
      },
    ],
    externalId: "supplier_invoice",
    id: DOCUMENT_TYPE_ID,
    name: "Supplier invoice",
    parameters: [
      { code: "pion", label: "Pion", value: "Finance" },
      { code: "numer_wewnetrzny", label: "Numer wewnętrzny", value: "ABC/1" },
    ],
    status: "active",
    updatedAt: "2026-07-03T10:00:00Z",
  };
}
