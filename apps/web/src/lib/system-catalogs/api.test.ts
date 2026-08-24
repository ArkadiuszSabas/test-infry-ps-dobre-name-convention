import assert from "node:assert/strict";
import test from "node:test";

import { installFetchMock, jsonResponse } from "@/lib/api/test-helpers";

import { systemCatalogClient } from "./api";

const SUPPLIER_INVOICE_ID = "11111111-1111-1111-1111-111111111111";
const CONTRACT_NUMBER_ID = "22222222-2222-2222-2222-222222222222";
const PION_FIELD_ID = "33333333-3333-3333-3333-333333333333";
const PION_DICTIONARY_ID = "44444444-4444-4444-4444-444444444444";
const DISPLAY_MODE_ID = "55555555-5555-5555-5555-555555555555";

test("admin catalog client loads and saves system catalog definitions", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: systemCatalogDefinitionResponseBody(),
      meta: {},
    }),
    jsonResponse({
      data: systemCatalogDefinitionResponseBody(),
      meta: {},
    }),
    jsonResponse({
      data: {
        definition: systemCatalogDefinitionResponseBody(),
        options: [
          {
            displayModeId: DISPLAY_MODE_ID,
            extensionValues: [
              {
                displayValue: "Finance",
                extensionFieldId: PION_FIELD_ID,
                textValue: null,
              },
            ],
            id: SUPPLIER_INVOICE_ID,
            label: "Supplier invoice - Finance",
            name: "Supplier invoice",
            parameters: [{ code: "pion", label: "Pion", value: "Finance" }],
          },
        ],
      },
      meta: {
        returnedCount: 1,
        systemCatalogKey: "document_type",
      },
    }),
  ]);
  t.after(fetchMock.restore);

  const definition =
    await systemCatalogClient.getSystemCatalogDefinition("document_type");
  await systemCatalogClient.saveSystemCatalogDefinition(
    "document_type",
    {
      displayModes: [
        {
          isActive: true,
          isDefault: true,
          name: "Typ - Pion",
          parts: [
            {
              partOrder: 0,
              sourceType: "base_name",
            },
            {
              extensionFieldCode: "pion",
              partOrder: 1,
              separatorBefore: " - ",
              sourceType: "extension_field",
            },
          ],
        },
      ],
      fields: [
        {
          code: "pion",
          dictionaryId: PION_DICTIONARY_ID,
          fieldOrder: 0,
          isActive: true,
          isRequired: true,
          label: "Pion",
          mappedAttributeDefinitionId: CONTRACT_NUMBER_ID,
          showInOverview: true,
          valueType: "dictionary",
        },
      ],
    },
    { csrfToken: "raw-csrf-token" },
  );
  const options =
    await systemCatalogClient.listSystemCatalogOptions("document_type");

  assert.equal(definition.fields[0]?.valueType, "dictionary");
  assert.equal(
    definition.displayModes[0]?.parts[1]?.extensionFieldId,
    PION_FIELD_ID,
  );
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/system-catalogs/document_type/definition",
  );
  assert.equal(fetchMock.calls[1]?.init.method, "PUT");
  assert.deepEqual(JSON.parse(String(fetchMock.calls[1]?.init.body)), {
    displayModes: [
      {
        isActive: true,
        isDefault: true,
        name: "Typ - Pion",
        parts: [
          {
            partOrder: 0,
            sourceType: "base_name",
          },
          {
            extensionFieldCode: "pion",
            partOrder: 1,
            separatorBefore: " - ",
            sourceType: "extension_field",
          },
        ],
      },
    ],
    fields: [
      {
        code: "pion",
        dictionaryId: PION_DICTIONARY_ID,
        fieldOrder: 0,
        isActive: true,
        isRequired: true,
        label: "Pion",
        mappedAttributeDefinitionId: CONTRACT_NUMBER_ID,
        showInOverview: true,
        valueType: "dictionary",
      },
    ],
  });
  assert.equal(options.data.options[0]?.label, "Supplier invoice - Finance");
  assert.equal(options.data.options[0]?.name, "Supplier invoice");
  assert.equal(
    options.data.options[0]?.extensionValues[0]?.extensionFieldId,
    PION_FIELD_ID,
  );
  assert.equal(options.data.definition.displayModes[0]?.name, "Typ - Pion");
  assert.equal(options.meta.returnedCount, 1);
});

function systemCatalogDefinitionResponseBody() {
  return {
    displayModes: [
      {
        created_at: "2026-07-03T10:00:00Z",
        id: DISPLAY_MODE_ID,
        isActive: true,
        isDefault: true,
        name: "Typ - Pion",
        parts: [
          {
            displayModeId: DISPLAY_MODE_ID,
            extensionFieldId: null,
            id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            partOrder: 0,
            separatorBefore: null,
            sourceType: "base_name",
          },
          {
            displayModeId: DISPLAY_MODE_ID,
            extensionFieldId: PION_FIELD_ID,
            id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            partOrder: 1,
            separatorBefore: " - ",
            sourceType: "extension_field",
          },
        ],
        systemCatalogKey: "document_type",
        updated_at: "2026-07-03T10:00:00Z",
      },
    ],
    fields: [
      {
        code: "pion",
        created_at: "2026-07-03T10:00:00Z",
        dictionaryId: PION_DICTIONARY_ID,
        fieldOrder: 0,
        id: PION_FIELD_ID,
        isActive: true,
        isRequired: true,
        label: "Pion",
        mappedAttributeDefinitionId: CONTRACT_NUMBER_ID,
        showInOverview: true,
        systemCatalogKey: "document_type",
        updated_at: "2026-07-03T10:00:00Z",
        valueType: "dictionary",
      },
    ],
    systemCatalogKey: "document_type",
  };
}
