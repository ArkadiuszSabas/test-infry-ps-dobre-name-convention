import assert from "node:assert/strict";
import test from "node:test";

import { reviewClient } from "./api";

test("review client maps GET fields, validation, sources and approval", async (t) => {
  const fetchMock = installFetchMock([jsonResponse(reviewEnvelope())]);
  t.after(fetchMock.restore);

  const result = await reviewClient.getDocumentReview("document-1");

  assert.equal(result.dataSource, "pipeline");
  assert.equal(result.processingStatus, "completed");
  assert.equal(result.schemaVersion, 2);
  assert.equal(result.version, 2);
  assert.equal(result.fields[0]?.attributeExternalId, "nip");
  assert.equal(result.fields[0]?.confidence, 0.96);
  assert.equal(result.fields[0]?.validations[0]?.message, "Invalid value");
  assert.equal(result.fields[0]?.sources[0]?.pageNumber, 1);
  assert.equal(result.approval?.steps[0]?.reviewerActorId, "reviewer-1");
  assert.equal(result.approval?.history[0]?.decision, "rejected");
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents/document-1/review",
  );
});

test("review client saves the complete list with expected version and CSRF", async (t) => {
  const fetchMock = installFetchMock([jsonResponse(reviewEnvelope())]);
  t.after(fetchMock.restore);

  await reviewClient.saveDocumentReview(
    "document-1",
    {
      expectedVersion: 2,
      fields: [
        { dataType: "string", id: "field-1", label: "NIP", value: "123" },
      ],
    },
    { csrfToken: "csrf-token" },
  );

  assert.equal(fetchMock.calls[0]?.init.method, "PUT");
  assert.equal(
    new Headers(fetchMock.calls[0]?.init.headers).get("X-CSRF-Token"),
    "csrf-token",
  );
  assert.deepEqual(JSON.parse(String(fetchMock.calls[0]?.init.body)), {
    expected_version: 2,
    fields: [
      { data_type: "string", id: "field-1", label: "NIP", value: "123" },
    ],
  });
});

test("review client submits approval decisions with CSRF", async (t) => {
  const fetchMock = installFetchMock([jsonResponse(reviewEnvelope())]);
  t.after(fetchMock.restore);

  await reviewClient.decideApproval(
    "document-1",
    "reject",
    "Missing value",
    2,
    { csrfToken: "csrf-token" },
  );

  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/documents/document-1/review/reject",
  );
  assert.equal(fetchMock.calls[0]?.init.method, "POST");
  assert.equal(
    new Headers(fetchMock.calls[0]?.init.headers).get("X-CSRF-Token"),
    "csrf-token",
  );
  assert.deepEqual(JSON.parse(String(fetchMock.calls[0]?.init.body)), {
    comment: "Missing value",
    expected_review_version: 2,
  });
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
    if (!response) throw new Error("Unexpected fetch call.");
    return response;
  }) as typeof fetch;
  return {
    calls,
    restore: () => {
      globalThis.fetch = originalFetch;
    },
  };
}

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
    status: 200,
  });
}

function reviewEnvelope() {
  return {
    data: {
      schema_version: 2,
      review_id: "review-1",
      document_id: "document-1",
      version: 2,
      data_source: "pipeline",
      processing_status: "completed",
      attributes_available: true,
      unavailable_reason_code: null,
      attributes: [
        {
          id: "field-1",
          kind: "configured",
          attribute_id: "attribute-1",
          attribute_external_id: "nip",
          label: "NIP",
          data_type: "string",
          required: true,
          display_order: 10,
          value: "123",
          display_value: "123",
          confidence: 0.96,
          status: "present",
          requires_review: true,
          review_reason_codes: ["INVALID_VALUE"],
          sources: [
            {
              kind: "ocr_key_value_pair",
              page_number: 1,
              order_index: 4,
              coordinate_system: "normalized_0_1",
              bounding_polygon: [
                0.08, 0.12, 0.31, 0.12, 0.31, 0.16, 0.08, 0.16,
              ],
              confidence: 0.96,
              source_key: "NIP",
            },
          ],
          value_source: "pipeline",
          manually_edited: false,
        },
      ],
      quality_score: 0.5,
      validations: [
        {
          code: "INVALID_VALUE",
          severity: "error",
          field_id: "field-1",
          message: "Invalid value",
        },
      ],
      created_at: "2026-07-15T10:00:00Z",
      updated_at: "2026-07-15T10:00:00Z",
      updated_by_actor_id: null,
      approval: {
        run_number: 2,
        status: "waiting_for_second_approval",
        is_current_actor_active_reviewer: true,
        steps: [
          {
            number: 1,
            status: "approved",
            reviewer_actor_id: "reviewer-1",
            decided_at: "2026-07-17T08:00:00Z",
            comment: "Looks good",
            reviewer_display_name: "Reviewer One",
          },
          {
            number: 2,
            status: "pending",
            reviewer_actor_id: "reviewer-2",
            decided_at: null,
            comment: null,
            reviewer_display_name: "Reviewer Two",
          },
        ],
        history: [
          {
            run_number: 1,
            step_number: 1,
            decision: "rejected",
            actor_id: "reviewer-1",
            comment: "Missing amount",
            decided_at: "2026-07-16T08:00:00Z",
            actor_display_name: "Reviewer One",
          },
        ],
      },
    },
    meta: {},
  };
}
