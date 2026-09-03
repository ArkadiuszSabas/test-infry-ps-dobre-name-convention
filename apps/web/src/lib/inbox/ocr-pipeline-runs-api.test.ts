import assert from "node:assert/strict";
import test from "node:test";

import { inboxClient } from "./api";
import type { OcrPipelineRunDto } from "./types";

test("inbox client starts document OCR pipeline runs with CSRF", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({ data: ocrRunDtoFixture(), meta: {} }, { status: 202 }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.startDocumentOcrPipelineRun(
    "33333333-3333-3333-3333-333333333333",
    {
      csrfToken: "raw-csrf-token",
      pipelineId: "77777777-7777-7777-7777-777777777777",
    },
  );

  assert.equal(result.id, "99999999-9999-9999-9999-999999999999");
  assert.equal(result.documentId, "33333333-3333-3333-3333-333333333333");
  assert.equal(result.steps[0]?.stepId, "preflight");
  assert.equal(result.steps[0]?.displayName, "Prepare document");
  assert.equal(result.pipelineName, "Invoice OCR");
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents/33333333-3333-3333-3333-333333333333/ocr/pipeline-runs",
  );
  assert.equal(fetchMock.calls[0]?.init.method, "POST");
  assert.deepEqual(JSON.parse(String(fetchMock.calls[0]?.init.body)), {
    pipeline_id: "77777777-7777-7777-7777-777777777777",
  });
  assert.equal(
    new Headers(fetchMock.calls[0]?.init.headers).get("X-CSRF-Token"),
    "raw-csrf-token",
  );
});

test("inbox client lists published OCR pipeline options", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        pipelines: [
          {
            id: "77777777-7777-7777-7777-777777777777",
            name: "Invoice OCR",
            published_version: 3,
            is_default: true,
          },
        ],
      },
      meta: { total_count: 1 },
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.listPublishedOcrPipelines();

  assert.deepEqual(result.data.pipelines[0], {
    id: "77777777-7777-7777-7777-777777777777",
    isDefault: true,
    name: "Invoice OCR",
    publishedVersion: 3,
  });
  assert.equal(fetchMock.calls[0]?.input, "/api/docmind/ocr/pipelines");
});

test("inbox client lists document OCR pipeline runs", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        runs: [
          ocrRunDtoFixture({
            diagnostics: [
              {
                code: "PAGE_WARNING",
                message: "Page 2 produced a safe warning.",
                path: "pages[1]",
                severity: "warning",
                step_id: "ocr",
              },
            ],
            status: "partial_failed",
          }),
        ],
      },
      meta: {
        document_id: "33333333-3333-3333-3333-333333333333",
        returned_count: 1,
        limit: 2,
        offset: 5,
        has_more: false,
      },
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.listDocumentOcrPipelineRuns(
    "33333333-3333-3333-3333-333333333333",
    { limit: 2, offset: 5 },
  );

  assert.equal(result.meta.documentId, "33333333-3333-3333-3333-333333333333");
  assert.equal(result.data.runs[0]?.status, "partial_failed");
  assert.equal(result.data.runs[0]?.diagnostics[0]?.stepId, "ocr");
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents/33333333-3333-3333-3333-333333333333/ocr/pipeline-runs?limit=2&offset=5",
  );
});

test("inbox client gets OCR pipeline run status", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({ data: ocrRunDtoFixture({ status: "running" }), meta: {} }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.getOcrPipelineRun(
    "99999999-9999-9999-9999-999999999999",
  );

  assert.equal(result.status, "running");
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/ocr/pipeline-runs/99999999-9999-9999-9999-999999999999",
  );
});

test("inbox client cancels an OCR pipeline run with CSRF", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: ocrRunDtoFixture({ status: "cancelling" }),
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.cancelOcrPipelineRun(
    "99999999-9999-9999-9999-999999999999",
    { csrfToken: "raw-csrf-token" },
  );

  assert.equal(result.status, "cancelling");
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/ocr/pipeline-runs/99999999-9999-9999-9999-999999999999/cancel",
  );
  assert.equal(fetchMock.calls[0]?.init.method, "POST");
  assert.equal(
    new Headers(fetchMock.calls[0]?.init.headers).get("X-CSRF-Token"),
    "raw-csrf-token",
  );
});

test("inbox client gets OCR pipeline run result availability", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        run: ocrRunDtoFixture({
          result_availability: "not_available",
          result_unavailable_reason_code: "RUN_NOT_FINISHED",
        }),
        result_available: false,
        unavailable_reason_code: "RUN_NOT_FINISHED",
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await inboxClient.getOcrPipelineRunResult(
    "99999999-9999-9999-9999-999999999999",
  );

  assert.equal(result.data.resultAvailable, false);
  assert.equal(result.data.unavailableReasonCode, "RUN_NOT_FINISHED");
  assert.equal(result.data.run.resultUnavailableReasonCode, "RUN_NOT_FINISHED");
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

function ocrRunDtoFixture(
  overrides: Partial<OcrPipelineRunDto> = {},
): OcrPipelineRunDto {
  return {
    catalog_hash: "catalog-hash-v1",
    catalog_version: "catalog-v1",
    completed_at: null,
    created_at: "2026-07-01T09:00:00Z",
    diagnostics: [],
    document_id: "33333333-3333-3333-3333-333333333333",
    error: null,
    id: "99999999-9999-9999-9999-999999999999",
    metrics: {},
    pipeline_id: "77777777-7777-7777-7777-777777777777",
    pipeline_name: "Invoice OCR",
    pipeline_version: 1,
    result_availability: "not_available",
    result_unavailable_reason_code: "RUN_NOT_FINISHED",
    started_at: null,
    status: "pending",
    steps: [
      {
        display_name: "Prepare document",
        duration_seconds: null,
        error: null,
        implementation_id: "document.preflight.prepare",
        metrics: {},
        status: "pending",
        step_id: "preflight",
        step_type: "preflight",
      },
    ],
    updated_at: "2026-07-01T09:00:00Z",
    ...overrides,
  };
}
