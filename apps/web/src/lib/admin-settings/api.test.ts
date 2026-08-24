import assert from "node:assert/strict";
import test from "node:test";

import { adminCatalogClient } from "./api";
import { installFetchMock, jsonResponse } from "@/lib/api/test-helpers";

const SUPPLIER_INVOICE_ID = "11111111-1111-1111-1111-111111111111";
const CONTRACT_NUMBER_ID = "22222222-2222-2222-2222-222222222222";
const GROSS_AMOUNT_ID = "33333333-3333-3333-3333-333333333333";
const REQUIREMENT_ID = "44444444-4444-4444-4444-444444444444";
const ATTRIBUTE_CATEGORY_ID = "55555555-5555-5555-5555-555555555555";

test("admin catalog client lists attributes by category and updates typed metadata", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        attributes: [
          {
            allowed_values: ["standard", "annex"],
            category: "Contract data",
            category_id: "99999999-9999-9999-9999-999999999999",
            comment: "Extracted from contract header.",
            constraints: { max_length: 80 },
            created_at: "2026-06-02T10:00:00Z",
            data_type: "string",
            dictionary_id: null,
            external_id: "contract_number",
            id: CONTRACT_NUMBER_ID,
            llm_context: "Read the header.\nPreserve formatting.",
            name: "Contract number",
            schema_version: 1,
            source: "ai",
            status: "active",
            updated_at: "2026-06-02T10:00:00Z",
            value_source: "inline_allowed_values",
          },
        ],
      },
      meta: {
        category_counts: [{ category: "Contract data", count: 1 }],
        total_count: 1,
      },
    }),
    jsonResponse({
      data: {
        allowed_values: ["standard"],
        category: "Contract data",
        category_id: "99999999-9999-9999-9999-999999999999",
        comment: null,
        constraints: { max_length: 80 },
        created_at: "2026-06-02T10:00:00Z",
        data_type: "string",
        dictionary_id: null,
        external_id: "contract_number",
        id: CONTRACT_NUMBER_ID,
        llm_context: "Read the table.\nReturn the exact value.",
        name: "Contract number",
        schema_version: 2,
        source: "user",
        status: "active",
        updated_at: "2026-06-02T11:00:00Z",
        value_source: "inline_allowed_values",
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await adminCatalogClient.listAttributes({
    category: "Contract data",
  });
  await adminCatalogClient.updateAttribute(
    CONTRACT_NUMBER_ID,
    {
      allowedValues: ["standard"],
      categoryId: "99999999-9999-9999-9999-999999999999",
      comment: null,
      constraints: { max_length: 80 },
      dataType: "string",
      dictionaryId: null,
      externalId: "agreement_number",
      llmContext: "Read the table.\nReturn the exact value.",
      name: "Contract number",
      source: "user",
      valueSource: "inline_allowed_values",
    },
    { csrfToken: "raw-csrf-token" },
  );

  assert.equal(result.meta.categoryCounts[0]?.category, "Contract data");
  assert.equal(
    result.data.attributes[0]?.categoryId,
    "99999999-9999-9999-9999-999999999999",
  );
  assert.equal(
    result.data.attributes[0]?.llmContext,
    "Read the header.\nPreserve formatting.",
  );
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/attributes?category=Contract+data",
  );
  assert.equal(fetchMock.calls[1]?.init.method, "PATCH");
  assert.deepEqual(JSON.parse(String(fetchMock.calls[1]?.init.body)), {
    allowed_values: ["standard"],
    category_id: "99999999-9999-9999-9999-999999999999",
    comment: null,
    constraints: { max_length: 80 },
    data_type: "string",
    dictionary_id: null,
    external_id: "agreement_number",
    llm_context: "Read the table.\nReturn the exact value.",
    name: "Contract number",
    source: "user",
    value_source: "inline_allowed_values",
  });
});

test("admin catalog client manages attribute categories", async (t) => {
  const categoryBody = {
    created_at: "2026-07-01T10:00:00Z",
    external_id: "metadata",
    flags: { isMetadata: true },
    id: ATTRIBUTE_CATEGORY_ID,
    label: "Metadata",
    status: "active",
    updated_at: "2026-07-01T10:00:00Z",
  };
  const fetchMock = installFetchMock([
    jsonResponse({
      data: { categories: [categoryBody] },
      meta: {
        active_count: 1,
        inactive_count: 0,
        returned_count: 1,
        status: "all",
        total_count: 1,
      },
    }),
    jsonResponse({ data: categoryBody, meta: {} }, { status: 201 }),
    jsonResponse({ data: categoryBody, meta: {} }),
    jsonResponse({
      data: { ...categoryBody, status: "inactive" },
      meta: {},
    }),
    jsonResponse({
      data: { deleted: true, id: ATTRIBUTE_CATEGORY_ID },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await adminCatalogClient.listAttributeCategories({
    status: "all",
  });
  await adminCatalogClient.createAttributeCategory(
    {
      externalId: "metadata",
      flags: { isMetadata: true },
      label: "Metadata",
    },
    { csrfToken: "raw-csrf-token" },
  );
  await adminCatalogClient.updateAttributeCategory(
    ATTRIBUTE_CATEGORY_ID,
    {
      flags: { isMetadata: true },
      label: "Metadata",
    },
    { csrfToken: "raw-csrf-token" },
  );
  await adminCatalogClient.deactivateAttributeCategory(ATTRIBUTE_CATEGORY_ID, {
    csrfToken: "raw-csrf-token",
  });
  await adminCatalogClient.deleteAttributeCategory(ATTRIBUTE_CATEGORY_ID, {
    csrfToken: "raw-csrf-token",
  });

  assert.equal(result.data.categories[0]?.id, ATTRIBUTE_CATEGORY_ID);
  assert.equal(result.data.categories[0]?.label, "Metadata");
  assert.equal(result.meta.totalCount, 1);
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/attributes/categories?status=all",
  );
  assert.equal(fetchMock.calls[1]?.init.method, "POST");
  assert.equal(fetchMock.calls[2]?.init.method, "PATCH");
  assert.equal(fetchMock.calls[3]?.init.method, "POST");
  assert.equal(fetchMock.calls[4]?.init.method, "DELETE");
  assert.deepEqual(JSON.parse(String(fetchMock.calls[1]?.init.body)), {
    external_id: "metadata",
    flags: { isMetadata: true },
    label: "Metadata",
  });
});

test("admin catalog client omits unchanged legacy fields from patch payload", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        allowed_values: [],
        category: "Legacy",
        category_id: null,
        comment: "Only comment changed.",
        constraints: {},
        created_at: "2026-06-02T10:00:00Z",
        data_type: "legacy_scalar",
        dictionary_id: null,
        external_id: "legacy_total",
        id: "55555555-5555-5555-5555-555555555555",
        llm_context: "x".repeat(1001),
        name: "Legacy total",
        schema_version: 1,
        source: "ai",
        status: "active",
        updated_at: "2026-06-02T11:00:00Z",
        value_source: "free_text",
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  await adminCatalogClient.updateAttribute(
    "55555555-5555-5555-5555-555555555555",
    {
      allowedValues: [],
      categoryId: null,
      comment: "Only comment changed.",
      constraints: {},
      dictionaryId: null,
      name: "Legacy total",
      source: "ai",
      valueSource: "free_text",
    },
    { csrfToken: "raw-csrf-token" },
  );

  const payload = JSON.parse(String(fetchMock.calls[0]?.init.body)) as Record<
    string,
    unknown
  >;

  assert.equal(fetchMock.calls[0]?.init.method, "PATCH");
  assert.equal("data_type" in payload, false);
  assert.equal("llm_context" in payload, false);
});

test("admin catalog client loads and saves attribute requirement matrices", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(matrixResponseBody()),
    jsonResponse(matrixResponseBody()),
  ]);
  t.after(fetchMock.restore);

  const result =
    await adminCatalogClient.getAttributeRequirements(SUPPLIER_INVOICE_ID);
  await adminCatalogClient.saveAttributeRequirements(
    SUPPLIER_INVOICE_ID,
    [
      {
        attributeDefinitionId: CONTRACT_NUMBER_ID,
        missingRequiredAction: "block_approval",
        required: true,
      },
      {
        attributeDefinitionId: GROSS_AMOUNT_ID,
        required: false,
      },
    ],
    { csrfToken: "raw-csrf-token" },
  );

  assert.equal(result.meta.assignedAttributeCount, 1);
  assert.equal(
    fetchMock.calls[0]?.input,
    `/api/docmind/document-types/${SUPPLIER_INVOICE_ID}/attribute-requirements`,
  );
  assert.equal(fetchMock.calls[0]?.init.method, "GET");
  assert.equal(fetchMock.calls[1]?.init.method, "PATCH");
  assert.equal(
    new Headers(fetchMock.calls[1]?.init.headers).get("X-CSRF-Token"),
    "raw-csrf-token",
  );
  assert.deepEqual(JSON.parse(String(fetchMock.calls[1]?.init.body)), {
    requirements: [
      {
        attribute_definition_id: CONTRACT_NUMBER_ID,
        include_metadata_in_context_resolver: false,
        missing_required_action: "block_approval",
        required: true,
      },
      {
        attribute_definition_id: GROSS_AMOUNT_ID,
        include_metadata_in_context_resolver: false,
        required: false,
      },
    ],
  });
});

function matrixResponseBody() {
  return {
    data: {
      document_type: {
        external_id: "supplier_invoice",
        id: SUPPLIER_INVOICE_ID,
        name: "Supplier invoice",
        status: "active",
      },
      requirements: [
        {
          attribute: {
            category: "Contract data",
            external_id: "contract_number",
            id: CONTRACT_NUMBER_ID,
            name: "Contract number",
            status: "active",
          },
          created_at: "2026-06-05T10:00:00Z",
          external_id: "requirement_11111111111111111111111111111111",
          id: REQUIREMENT_ID,
          missing_required_action: "block_approval",
          required: true,
          updated_at: "2026-06-05T10:00:00Z",
        },
      ],
      unassigned_attributes: [
        {
          category: "Financial data",
          external_id: "gross_amount",
          id: GROSS_AMOUNT_ID,
          name: "Gross amount",
          status: "active",
        },
      ],
    },
    meta: {
      assigned_attribute_count: 1,
      document_type_id: SUPPLIER_INVOICE_ID,
      optional_attribute_count: 0,
      required_attribute_count: 1,
      total_attribute_count: 2,
      unassigned_attribute_count: 1,
    },
  };
}
