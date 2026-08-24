import assert from "node:assert/strict";
import test from "node:test";

import { installFetchMock, jsonResponse } from "@/lib/api/test-helpers";

import { adminCatalogClient } from "./api";

const SUPPLIER_INVOICE_ID = "11111111-1111-1111-1111-111111111111";
const CONTRACT_NUMBER_ID = "22222222-2222-2222-2222-222222222222";
const PION_FIELD_ID = "66666666-6666-6666-6666-666666666666";
const PION_DICTIONARY_ID = "77777777-7777-7777-7777-777777777777";
const PION_ENTRY_ID = "88888888-8888-8888-8888-888888888888";
const DISPLAY_MODE_ID = "99999999-9999-9999-9999-999999999999";

test("admin catalog client lists document types by lifecycle status", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        document_types: [
          documentTypeResponseBody({
            description: "Optional description",
            displayLabel: "Supplier invoice - Finance",
            displayModeId: DISPLAY_MODE_ID,
            extensionValues: [
              {
                code: "pion",
                dictionaryEntryId: PION_ENTRY_ID,
                dictionaryId: PION_DICTIONARY_ID,
                displayValue: "Finance",
                extensionFieldId: PION_FIELD_ID,
                fieldOrder: 0,
                label: "Pion",
                showInOverview: true,
                textValue: null,
                valueType: "dictionary",
              },
            ],
            parameters: [{ code: "pion", label: "Pion", value: "Finance" }],
          }),
        ],
      },
      meta: {
        active_count: 1,
        inactive_count: 0,
        returned_count: 1,
        status: "active",
        total_count: 1,
      },
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await adminCatalogClient.listDocumentTypes({
    status: "active",
  });

  assert.equal(result.data.documentTypes[0]?.id, SUPPLIER_INVOICE_ID);
  assert.equal(result.data.documentTypes[0]?.externalId, "supplier_invoice");
  assert.equal(
    result.data.documentTypes[0]?.displayLabel,
    "Supplier invoice - Finance",
  );
  assert.equal(
    result.data.documentTypes[0]?.extensionValues[0]?.dictionaryEntryId,
    PION_ENTRY_ID,
  );
  assert.equal(result.data.documentTypes[0]?.parameters[0]?.value, "Finance");
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/document-types?status=active",
  );
  assert.equal(fetchMock.calls[0]?.init.method, "GET");
});

test("admin catalog client sends CSRF protected document type mutations", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(
      {
        data: documentTypeResponseBody(),
        meta: {},
      },
      { status: 201 },
    ),
    jsonResponse({
      data: {
        id: SUPPLIER_INVOICE_ID,
        deleted: true,
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  await adminCatalogClient.createDocumentType(
    {
      description: null,
      externalId: "supplier_invoice",
      name: "Supplier invoice",
    },
    { csrfToken: "raw-csrf-token" },
  );
  await adminCatalogClient.deleteDocumentType(SUPPLIER_INVOICE_ID, {
    csrfToken: "raw-csrf-token",
  });

  assert.equal(fetchMock.calls[0]?.init.method, "POST");
  assert.equal(fetchMock.calls[1]?.init.method, "DELETE");
  assert.equal(
    new Headers(fetchMock.calls[0]?.init.headers).get("X-CSRF-Token"),
    "raw-csrf-token",
  );
  assert.deepEqual(JSON.parse(String(fetchMock.calls[0]?.init.body)), {
    description: null,
    external_id: "supplier_invoice",
    name: "Supplier invoice",
  });
});

test("admin catalog client omits blank optional external IDs", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(
      {
        data: documentTypeResponseBody({ external_id: null }),
        meta: {},
      },
      { status: 201 },
    ),
    jsonResponse({
      data: {
        allowed_values: [],
        category: "Contract data",
        category_id: null,
        comment: null,
        constraints: {},
        created_at: "2026-06-02T10:00:00Z",
        data_type: "string",
        dictionary_id: null,
        external_id: null,
        id: CONTRACT_NUMBER_ID,
        llm_context: null,
        name: "Contract number",
        schema_version: 1,
        source: "ai",
        status: "active",
        updated_at: "2026-06-02T10:00:00Z",
        value_source: "free_text",
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  await adminCatalogClient.createDocumentType({
    description: null,
    externalId: null,
    name: "Supplier invoice",
  });
  await adminCatalogClient.createAttribute({
    allowedValues: [],
    categoryId: null,
    comment: null,
    constraints: {},
    dataType: "string",
    dictionaryId: null,
    externalId: null,
    llmContext: null,
    name: "Contract number",
    source: "ai",
    valueSource: "free_text",
  });

  assert.deepEqual(JSON.parse(String(fetchMock.calls[0]?.init.body)), {
    description: null,
    name: "Supplier invoice",
  });
  assert.deepEqual(JSON.parse(String(fetchMock.calls[1]?.init.body)), {
    allowed_values: [],
    category_id: null,
    comment: null,
    constraints: {},
    data_type: "string",
    dictionary_id: null,
    llm_context: null,
    name: "Contract number",
    source: "ai",
    value_source: "free_text",
  });
});

test("admin catalog client sends document type extension values when provided", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(
      {
        data: documentTypeResponseBody({
          displayLabel: "Supplier invoice - Finance",
        }),
        meta: {},
      },
      { status: 201 },
    ),
    jsonResponse({
      data: documentTypeResponseBody({
        description: "Updated",
      }),
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  await adminCatalogClient.createDocumentType(
    {
      description: null,
      externalId: "supplier_invoice",
      extensionValues: [
        {
          dictionaryEntryId: PION_ENTRY_ID,
          extensionFieldId: PION_FIELD_ID,
        },
      ],
      name: "Supplier invoice",
    },
    { csrfToken: "raw-csrf-token" },
  );
  await adminCatalogClient.updateDocumentType(
    SUPPLIER_INVOICE_ID,
    {
      description: "Updated",
      externalId: "vendor_invoice",
      extensionValues: [],
      name: "Supplier invoice",
    },
    { csrfToken: "raw-csrf-token" },
  );

  assert.deepEqual(JSON.parse(String(fetchMock.calls[0]?.init.body)), {
    description: null,
    extensionValues: [
      {
        dictionaryEntryId: PION_ENTRY_ID,
        extensionFieldId: PION_FIELD_ID,
      },
    ],
    external_id: "supplier_invoice",
    name: "Supplier invoice",
  });
  assert.deepEqual(JSON.parse(String(fetchMock.calls[1]?.init.body)), {
    description: "Updated",
    external_id: "vendor_invoice",
    extensionValues: [],
    name: "Supplier invoice",
  });
});

function documentTypeResponseBody(overrides: Record<string, unknown> = {}) {
  return {
    created_at: "2026-05-29T10:00:00Z",
    description: null,
    displayLabel: "Supplier invoice",
    displayModeId: null,
    extensionValues: [],
    external_id: "supplier_invoice",
    id: SUPPLIER_INVOICE_ID,
    name: "Supplier invoice",
    parameters: [],
    status: "active",
    updated_at: "2026-05-29T10:00:00Z",
    ...overrides,
  };
}
