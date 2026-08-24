import assert from "node:assert/strict";
import test from "node:test";

import { inboxClient } from "./api";

const SUPPLIER_INVOICE_ID = "11111111-1111-1111-1111-111111111111";

test("inbox client lists documents from every source", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        documents: [
          {
            archive_url: "https://tenant.sharepoint.com/archive/invoice.pdf",
            connector: "manual_upload",
            connector_name: "Manual upload",
            connector_correlation_id: null,
            content_size_bytes: 128,
            created_at: "2026-06-16T10:00:00Z",
            document_type_external_id: "supplier_invoice",
            document_type_id: SUPPLIER_INVOICE_ID,
            document_type_name: "Supplier invoice",
            id: "33333333-3333-3333-3333-333333333333",
            name: "invoice.pdf",
            original_filename: "invoice.pdf",
            source: "manual_upload",
            status: "received",
            uploaded_by: {
              display_name: "admin@example.com",
              user_id: "11111111-1111-1111-1111-111111111111",
            },
            updated_at: "2026-06-16T10:00:00Z",
          },
          {
            connector: "sample_connector",
            connector_name: "Sample connector",
            connector_correlation_id: "9a375716-8a1d-4ed8-b8d3-1122ac154b0d",
            content_size_bytes: 256,
            created_at: "2026-07-20T13:09:46Z",
            document_type_external_id: "sample_contract",
            document_type_id: "898ffb04-4e04-48b9-9996-b5b6bc466a52",
            document_type_name: "Sample contract",
            id: "93182b91-3e3c-4074-8f37-8f259dc9c6a1",
            name: "sample-document",
            original_filename: "sample-contract.pdf",
            source: "sample_connector",
            status: "received",
            uploaded_by: null,
            updated_at: "2026-07-20T13:09:46Z",
          },
        ],
      },
      meta: {
        returned_count: 2,
        source: null,
        limit: 50,
        offset: 0,
        has_more: false,
      },
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.listDocuments();

  assert.equal(result.data.documents[0]?.source, "manual_upload");
  assert.equal(
    result.data.documents[0]?.archiveUrl,
    "https://tenant.sharepoint.com/archive/invoice.pdf",
  );
  assert.equal(result.data.documents[1]?.source, "sample_connector");
  assert.equal(
    result.data.documents[0]?.uploadedBy?.displayName,
    "admin@example.com",
  );
  assert.equal(result.data.documents[0]?.documentTypeId, SUPPLIER_INVOICE_ID);
  assert.equal(
    result.data.documents[0]?.documentTypeExternalId,
    "supplier_invoice",
  );
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents?archived=false&limit=50&offset=0",
  );
  assert.equal(fetchMock.calls[0]?.init.method, "GET");
});

test("inbox client lists a requested document window", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: { documents: [] },
      meta: {
        returned_count: 0,
        source: null,
        limit: 25,
        offset: 50,
        has_more: false,
      },
    }),
  ]);
  t.after(fetchMock.restore);

  await inboxClient.listDocuments({
    archived: true,
    limit: 25,
    offset: 50,
  });

  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents?archived=true&limit=25&offset=50",
  );
});

test("inbox client paginates documents until requested document is found", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: { documents: [documentFixture("first-page-document")] },
      meta: {
        returned_count: 1,
        source: null,
        limit: 100,
        offset: 0,
        has_more: true,
      },
    }),
    jsonResponse({
      data: {
        documents: [
          documentFixture("target-document"),
          documentFixture("next-document"),
        ],
      },
      meta: {
        returned_count: 2,
        source: null,
        limit: 100,
        offset: 1,
        has_more: false,
      },
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.findDocumentContext("target-document");

  assert.equal(
    result.documents.map((document) => document.id).join(","),
    ["first-page-document", "target-document", "next-document"].join(","),
  );
  assert.equal(fetchMock.calls.length, 2);
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents?archived=false&limit=100&offset=0",
  );
  assert.equal(
    fetchMock.calls[1]?.input,
    "/api/docmind/documents?archived=false&limit=100&offset=1",
  );
});

test("inbox client loads document details with metadata values", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        ...documentFixture("33333333-3333-3333-3333-333333333333"),
        external_id: "source-doc-10",
        metadata_values: {
          contract_number: "A/1",
          gross_amount: 123.45,
        },
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.getDocument(
    "33333333-3333-3333-3333-333333333333",
  );

  assert.equal(result.externalId, "source-doc-10");
  assert.deepEqual(result.metadataValues, {
    contract_number: "A/1",
    gross_amount: 123.45,
  });
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents/33333333-3333-3333-3333-333333333333",
  );
});

test("inbox client checks impact and permanently deletes with CSRF", async (t) => {
  const operation = {
    completed_at: "2026-07-28T10:00:00Z",
    created_at: "2026-07-28T09:59:00Z",
    document_id: "33333333-3333-3333-3333-333333333333",
    error_code: null,
    failure_stage: null,
    operation_id: "44444444-4444-4444-8444-444444444444",
    policy: "preserve",
    stage: "completed",
    state: "completed",
    updated_at: "2026-07-28T10:00:00Z",
    warning_code: "EXTERNAL_CONNECTOR_ARTIFACTS_PRESERVED",
  };
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        document_id: operation.document_id,
        operation: null,
        policy: "preserve",
        preparation_status: "ready",
        preserved_artifact_labels: ["SharePoint", "WEBCON"],
        error_code: null,
        warning_code: operation.warning_code,
      },
      meta: {},
    }),
    jsonResponse({ data: operation, meta: {} }),
  ]);
  t.after(fetchMock.restore);

  const impact = await inboxClient.getDocumentDeletionImpact(
    operation.document_id,
  );
  const result = await inboxClient.deleteDocument(operation.document_id, {
    csrfToken: "csrf-token",
  });

  assert.deepEqual(impact.data.preserved_artifact_labels, [
    "SharePoint",
    "WEBCON",
  ]);
  assert.equal(result.data.stage, "completed");
  assert.equal(
    fetchMock.calls[0]?.input,
    `/api/docmind/documents/${operation.document_id}/deletion`,
  );
  assert.equal(fetchMock.calls[0]?.init.method, "GET");
  assert.equal(
    fetchMock.calls[1]?.input,
    `/api/docmind/documents/${operation.document_id}`,
  );
  assert.equal(fetchMock.calls[1]?.init.method, "DELETE");
  assert.equal(
    new Headers(fetchMock.calls[1]?.init.headers).get("X-CSRF-Token"),
    "csrf-token",
  );
});

test("inbox client loads manual upload options", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        document_types: [
          {
            external_id: "supplier_invoice",
            id: SUPPLIER_INVOICE_ID,
            name: "Supplier invoice",
          },
        ],
      },
      meta: { returned_count: 1 },
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.listManualUploadOptions();

  assert.equal(result.data.documentTypes[0]?.id, SUPPLIER_INVOICE_ID);
  assert.equal(result.data.documentTypes[0]?.externalId, "supplier_invoice");
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents/manual-upload-options",
  );
});

test("inbox client loads manual upload metadata schema", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        document_type: {
          external_id: "supplier_invoice",
          id: SUPPLIER_INVOICE_ID,
          name: "Supplier invoice",
          status: "active",
        },
        fields: [
          {
            allowed_values: [],
            category: "Metadane",
            category_id: "77777777-7777-7777-7777-777777777777",
            constraints: { max_length: 80 },
            data_type: "string",
            dictionary_id: null,
            external_id: "contract_number",
            id: "22222222-2222-2222-2222-222222222222",
            key: "contract_number",
            label: "Contract number",
            required: true,
            schema_version: 1,
            status: "active",
            value_source: "free_text",
          },
          {
            allowed_values: [],
            category: "Metadane",
            category_id: "77777777-7777-7777-7777-777777777777",
            constraints: {},
            data_type: "number",
            dictionary_id: null,
            external_id: "gross_amount",
            id: "33333333-3333-3333-3333-333333333333",
            key: "gross_amount",
            label: "Gross amount",
            required: false,
            schema_version: 1,
            status: "active",
            value_source: "free_text",
          },
        ],
      },
      meta: {
        document_type_id: SUPPLIER_INVOICE_ID,
        field_count: 2,
        required_field_count: 1,
      },
    }),
  ]);
  t.after(fetchMock.restore);

  const result =
    await inboxClient.getManualUploadMetadataSchema(SUPPLIER_INVOICE_ID);

  assert.equal(result.data.documentType.id, SUPPLIER_INVOICE_ID);
  assert.equal(result.data.fields[0]?.key, "contract_number");
  assert.equal(result.data.fields[1]?.key, "gross_amount");
  assert.equal(result.data.fields[1]?.required, false);
  assert.equal(
    result.data.fields[0]?.categoryId,
    "77777777-7777-7777-7777-777777777777",
  );
  assert.equal(result.meta.fieldCount, 2);
  assert.equal(result.meta.requiredFieldCount, 1);
  assert.equal(
    fetchMock.calls[0]?.input,
    `/api/docmind/documents/manual-upload-metadata-schema?document_type_id=${SUPPLIER_INVOICE_ID}`,
  );
});

test("inbox client loads document metadata schema from document type endpoint", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        document_type: {
          external_id: "supplier_invoice",
          id: SUPPLIER_INVOICE_ID,
          name: "Supplier invoice",
          status: "active",
        },
        fields: [
          {
            allowed_values: [],
            category: "Metadane",
            constraints: { max_length: 80 },
            created_at: "2026-06-25T10:00:00Z",
            data_type: "string",
            dictionary_id: null,
            external_id: "contract_number",
            id: "22222222-2222-2222-2222-222222222222",
            key: "contract_number",
            label: "Contract number",
            required: true,
            schema_version: 1,
            status: "active",
            updated_at: "2026-06-25T10:00:00Z",
            value_source: "free_text",
          },
        ],
      },
      meta: {
        document_type_id: SUPPLIER_INVOICE_ID,
        field_count: 1,
        optional_field_count: 0,
        required_field_count: 1,
      },
    }),
  ]);
  t.after(fetchMock.restore);

  const result =
    await inboxClient.getDocumentMetadataSchema(SUPPLIER_INVOICE_ID);

  assert.equal(result.data.fields[0]?.key, "contract_number");
  assert.equal(result.data.fields[0]?.categoryId, undefined);
  assert.equal(result.data.fields[0]?.createdAt, "2026-06-25T10:00:00Z");
  assert.equal(
    fetchMock.calls[0]?.input,
    `/api/docmind/document-types/${SUPPLIER_INVOICE_ID}/metadata-schema`,
  );
});

test("inbox client loads active dictionary lookup entries", async (t) => {
  const dictionaryId = "88888888-8888-8888-8888-888888888888";
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        entries: [
          {
            dictionary_id: dictionaryId,
            external_id: "poland",
            id: "99999999-9999-9999-9999-999999999999",
            label: "Poland",
            sort_order: 1,
          },
        ],
      },
      meta: {
        has_more: true,
        limit: 100,
        offset: 0,
        returned_count: 1,
        total_count: 2,
      },
    }),
    jsonResponse({
      data: {
        entries: [
          {
            dictionary_id: dictionaryId,
            external_id: "germany",
            id: "99999999-9999-9999-9999-999999999998",
            label: "Germany",
            sort_order: 0,
          },
        ],
      },
      meta: {
        has_more: false,
        limit: 100,
        offset: 1,
        returned_count: 1,
        total_count: 2,
      },
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.listDictionaryLookupEntries(dictionaryId);

  assert.equal(result.data.entries[0]?.externalId, "poland");
  assert.equal(result.data.entries[1]?.externalId, "germany");
  assert.equal(result.data.entries[0]?.sortOrder, 1);
  assert.equal(result.data.entries[1]?.sortOrder, 0);
  assert.equal(result.meta.returnedCount, 2);
  assert.equal(fetchMock.calls.length, 2);
  assert.equal(
    fetchMock.calls[0]?.input,
    `/api/docmind/dictionaries/${dictionaryId}/lookup/entries?limit=100&offset=0`,
  );
  assert.equal(
    fetchMock.calls[1]?.input,
    `/api/docmind/dictionaries/${dictionaryId}/lookup/entries?limit=100&offset=1`,
  );
});

test("inbox client resolves a stored dictionary lookup entry", async (t) => {
  const dictionaryId = "88888888-8888-8888-8888-888888888888";
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        dictionary_id: dictionaryId,
        external_id: "poland",
        id: "99999999-9999-9999-9999-999999999999",
        label: "Poland",
        sort_order: null,
        status: "inactive",
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.resolveDictionaryLookupEntry(
    dictionaryId,
    "poland",
  );

  assert.equal(result.label, "Poland");
  assert.equal(result.sortOrder, null);
  assert.equal(
    fetchMock.calls[0]?.input,
    `/api/docmind/dictionaries/${dictionaryId}/lookup/entries/resolve?entry_external_id=poland`,
  );
});

test("inbox client uploads manual PDF files with CSRF", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(
      {
        data: {
          connector: "manual_upload",
          connector_correlation_id: null,
          content_size_bytes: 18,
          created_at: "2026-06-16T10:00:00Z",
          document_type_id: SUPPLIER_INVOICE_ID,
          id: "33333333-3333-3333-3333-333333333333",
          metadata_values: {},
          name: "invoice.pdf",
          original_filename: "invoice.pdf",
          source: "manual_upload",
          status: "received",
          storage_locator: "azblob://inbox/raw/invoice.pdf",
          uploaded_by: {
            display_name: "admin@example.com",
            user_id: "11111111-1111-1111-1111-111111111111",
          },
          updated_at: "2026-06-16T10:00:00Z",
        },
        meta: {},
      },
      { status: 201 },
    ),
  ]);
  t.after(fetchMock.restore);

  await inboxClient.uploadManualPdf(
    {
      documentTypeId: SUPPLIER_INVOICE_ID,
      file: new File([new Blob(["%PDF-1.7 pdf-bytes"])], "invoice.pdf", {
        type: "application/pdf",
      }),
      metadataValues: { contract_number: "A/1" },
    },
    { csrfToken: "raw-csrf-token" },
  );

  const request = fetchMock.calls[0];

  assert.equal(request?.input, "/api/docmind/documents/manual-upload");
  assert.equal(request?.init.method, "POST");
  assert.equal(
    new Headers(request?.init.headers).get("X-CSRF-Token"),
    "raw-csrf-token",
  );
  assert.ok(request?.init.body instanceof FormData);
  assert.equal(request.init.body.get("document_type_id"), SUPPLIER_INVOICE_ID);
  assert.equal(
    request.init.body.get("metadata_values"),
    JSON.stringify({ contract_number: "A/1" }),
  );
  assert.ok(request.init.body.get("file") instanceof File);
});

test("inbox client builds document PDF preview URLs", () => {
  assert.equal(
    inboxClient.buildDocumentPdfPreviewUrl(
      "33333333-3333-3333-3333-333333333333",
    ),
    "/api/docmind/documents/33333333-3333-3333-3333-333333333333/file",
  );
});

test("inbox client loads PDF preview blobs", async (t) => {
  const fetchMock = installFetchMock([
    new Response(
      new Blob(["%PDF-1.7 pdf-bytes"], { type: "application/pdf" }),
      {
        headers: { "content-type": "application/pdf" },
        status: 200,
      },
    ),
  ]);
  t.after(fetchMock.restore);

  const blob = await inboxClient.loadDocumentPdfPreview(
    "33333333-3333-3333-3333-333333333333",
  );

  assert.equal(blob.type, "application/pdf");
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents/33333333-3333-3333-3333-333333333333/file",
  );
  assert.equal(fetchMock.calls[0]?.init.method, "GET");
});

test("inbox client rejects non-PDF preview responses", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(
      {
        error: {
          code: "DOCUMENT_CONTENT_NOT_FOUND",
          details: {},
          message: "Document content was not found in storage.",
        },
      },
      { status: 404 },
    ),
  ]);
  t.after(fetchMock.restore);

  await assert.rejects(
    inboxClient.loadDocumentPdfPreview("33333333-3333-3333-3333-333333333333"),
    { code: "DOCUMENT_CONTENT_NOT_FOUND" },
  );
});

test("inbox client rejects PDF-like non-PDF media types", async (t) => {
  const fetchMock = installFetchMock([
    new Response("{}", {
      headers: { "content-type": "application/pdf+json" },
      status: 200,
    }),
  ]);
  t.after(fetchMock.restore);

  await assert.rejects(
    inboxClient.loadDocumentPdfPreview("33333333-3333-3333-3333-333333333333"),
    { code: "INVALID_API_RESPONSE" },
  );
});

interface FetchCall {
  input: string;
  init: RequestInit;
}

function installFetchMock(responses: Response[]) {
  const originalFetch = globalThis.fetch;
  const calls: FetchCall[] = [];

  globalThis.fetch = (async (input, init = {}) => {
    calls.push({ input: input.toString(), init });
    const response = responses.shift();

    if (!response) {
      throw new Error("Unexpected fetch call.");
    }

    return response;
  }) as typeof fetch;

  return {
    calls,
    restore: () => {
      globalThis.fetch = originalFetch;
    },
  };
}

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    headers: {
      "content-type": "application/json",
      ...init.headers,
    },
    status: init.status ?? 200,
    statusText: init.statusText,
  });
}

function documentFixture(id: string) {
  return {
    connector: "manual_upload",
    connector_name: "Manual upload",
    connector_correlation_id: null,
    content_size_bytes: 128,
    created_at: "2026-06-16T10:00:00Z",
    document_type_external_id: "supplier_invoice",
    document_type_id: SUPPLIER_INVOICE_ID,
    document_type_name: "Supplier invoice",
    id,
    name: `${id}.pdf`,
    original_filename: `${id}.pdf`,
    source: "manual_upload",
    status: "received",
    uploaded_by: {
      display_name: "admin@example.com",
      user_id: "11111111-1111-1111-1111-111111111111",
    },
    updated_at: "2026-06-16T10:00:00Z",
  };
}
