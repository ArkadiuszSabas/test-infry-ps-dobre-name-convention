import assert from "node:assert/strict";
import test from "node:test";

import { inboxClient } from "./api";

test("inbox client lists document OCR pipeline runs", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: { runs: [ocrRunFixture()] },
      meta: {
        document_id: "33333333-3333-3333-3333-333333333333",
        returned_count: 1,
        limit: 10,
        offset: 0,
        has_more: false,
      },
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.listDocumentOcrPipelineRuns(
    "33333333-3333-3333-3333-333333333333",
  );

  assert.equal(result.data.runs[0]?.id, "99999999-9999-9999-9999-999999999999");
  assert.equal(result.data.runs[0]?.resultAvailability, "available");
  assert.equal(result.meta.documentId, "33333333-3333-3333-3333-333333333333");
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents/33333333-3333-3333-3333-333333333333/ocr/pipeline-runs?limit=10&offset=0",
  );
});

test("inbox client loads OCR pipeline run result payloads", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        run: ocrRunFixture(),
        result_available: true,
        unavailable_reason_code: null,
        result: ocrResultFixture(),
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.loadOcrPipelineRunResult(
    "99999999-9999-9999-9999-999999999999",
  );

  assert.equal(result.data.resultAvailable, true);
  assert.equal(result.data.result?.providerId, "azure_document_intelligence");
  assert.equal(result.data.result?.pagesTruncated, false);
  assert.equal(result.data.result?.pages[0]?.text, "Invoice total 42");
  assert.deepEqual(result.data.result?.pages[0]?.warningCodes, [
    "LOW_CONFIDENCE_REGION",
  ]);
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/ocr/pipeline-runs/99999999-9999-9999-9999-999999999999/result",
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

function ocrRunFixture() {
  return {
    id: "99999999-9999-9999-9999-999999999999",
    document_id: "33333333-3333-3333-3333-333333333333",
    pipeline_id: "77777777-7777-7777-7777-777777777777",
    pipeline_version: 1,
    status: "succeeded",
    result_availability: "available",
    result_unavailable_reason_code: null,
    steps: [
      {
        step_id: "ocr",
        step_type: "ocr_parsing",
        implementation_id: "document.ocr.azure_document_intelligence",
        display_name: "Azure Document Intelligence OCR",
        status: "succeeded",
        duration_seconds: 0.1,
        metrics: { page_count: 1 },
        error: null,
      },
    ],
    metrics: { step_count: 1 },
    diagnostics: [],
    error: null,
    catalog_version: "catalog-v1",
    catalog_hash: "catalog-hash-v1",
    created_at: "2026-07-02T08:00:00Z",
    updated_at: "2026-07-02T08:01:00Z",
    started_at: "2026-07-02T08:00:00Z",
    completed_at: "2026-07-02T08:01:00Z",
  };
}

function ocrResultFixture() {
  return {
    status: "succeeded",
    provider_id: "azure_document_intelligence",
    model_id: "prebuilt-layout",
    total_page_count: 1,
    succeeded_page_count: 1,
    failed_page_count: 0,
    average_confidence: 0.91,
    low_confidence_page_count: 0,
    warning_count: 1,
    pages_truncated: false,
    pages: [
      {
        page_number: 1,
        status: "parsed",
        text: "Invoice total 42",
        text_truncated: false,
        lines: ["Invoice total", "42"],
        lines_truncated: false,
        confidence: 0.91,
        warning_codes: ["LOW_CONFIDENCE_REGION"],
        error_code: null,
        fallback_used: false,
        fallback_reason_codes: [],
        primary_error_code: null,
      },
    ],
  };
}
