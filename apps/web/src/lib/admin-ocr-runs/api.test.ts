import assert from "node:assert/strict";
import test from "node:test";

import { installFetchMock, jsonResponse } from "@/lib/api/test-helpers";

import { adminOcrRunsClient } from "./api";

test("admin OCR client maps filters and uses bounded admin routes", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: { runs: [] },
      meta: { has_more: false, limit: 25, offset: 25, returned_count: 0 },
    }),
    jsonResponse({ data: detailFixture(), meta: {} }),
  ]);
  t.after(fetchMock.restore);

  await adminOcrRunsClient.list({
    connector: "km-primary",
    documentTypeId: "type-7",
    limit: 25,
    offset: 25,
    search: "invoice 7",
    status: "running",
    view: "active",
  });
  await adminOcrRunsClient.detail("run/unsafe");

  const listUrl = String(fetchMock.calls[0]?.input);
  assert.match(listUrl, /^\/api\/docmind\/admin\/ocr\/pipeline-runs\?/);
  assert.equal(
    new URL(`https://test${listUrl}`).searchParams.get("search"),
    "invoice 7",
  );
  assert.equal(
    new URL(`https://test${listUrl}`).searchParams.get("offset"),
    "25",
  );
  assert.equal(
    new URL(`https://test${listUrl}`).searchParams.get("document_type_id"),
    "type-7",
  );
  assert.equal(
    fetchMock.calls[1]?.input,
    "/api/docmind/admin/ocr/pipeline-runs/run%2Funsafe",
  );
});

test("admin OCR client starts a selected pipeline and lists published choices", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({ data: { id: "new-run" }, meta: {} }),
    jsonResponse({
      data: {
        pipelines: [
          {
            id: "pipeline-1",
            is_default: true,
            name: "OCR Agentic",
            published_version: 4,
          },
        ],
      },
      meta: { total_count: 1 },
    }),
  ]);
  t.after(fetchMock.restore);

  const runId = await adminOcrRunsClient.start(
    "document/unsafe",
    "pipeline-1",
    {
      csrfToken: "csrf-token",
    },
  );
  const pipelines = await adminOcrRunsClient.listPublishedPipelines();

  assert.equal(runId, "new-run");
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents/document%2Funsafe/ocr/pipeline-runs",
  );
  assert.equal(fetchMock.calls[0]?.init.method, "POST");
  assert.equal(
    new Headers(fetchMock.calls[0]?.init.headers).get("X-CSRF-Token"),
    "csrf-token",
  );
  assert.deepEqual(JSON.parse(String(fetchMock.calls[0]?.init.body)), {
    pipeline_id: "pipeline-1",
  });
  assert.deepEqual(pipelines, [
    {
      id: "pipeline-1",
      isDefault: true,
      name: "OCR Agentic",
      publishedVersion: 4,
    },
  ]);
});

test("admin OCR client cancels through the existing CSRF protected endpoint", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({ data: { status: "cancelling" }, meta: {} }),
  ]);
  t.after(fetchMock.restore);

  const status = await adminOcrRunsClient.cancel("run-1", {
    csrfToken: "csrf-token",
  });

  assert.equal(status, "cancelling");
  assert.equal(fetchMock.calls[0]?.init.method, "POST");
  assert.equal(
    new Headers(fetchMock.calls[0]?.init.headers).get("X-CSRF-Token"),
    "csrf-token",
  );
});

function detailFixture() {
  return {
    attempts: [],
    cancellation: {
      requested_at: null,
      requested_by_actor_id: null,
      requested_by_actor_login: null,
    },
    diagnostics: [],
    error: null,
    metrics: {},
    run: {},
    steps: [],
  };
}
