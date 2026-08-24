import assert from "node:assert/strict";
import test from "node:test";

import { installFetchMock, jsonResponse } from "@/lib/api/test-helpers";

import { ocrPipelinesClient } from "./api";
import { mapValidationErrorDetails } from "./api-mappers";

const PIPELINE_ID = "11111111-1111-1111-1111-111111111111";

test("OCR pipeline client maps catalog and pipeline list envelopes", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(catalogEnvelope()),
    jsonResponse({
      data: {
        pipelines: [
          {
            archived_at: null,
            created_at: "2026-06-30T10:00:00Z",
            description: "Default path",
            has_draft: true,
            id: PIPELINE_ID,
            is_default: true,
            last_validation_valid: true,
            lifecycle: "published",
            name: "Default OCR",
            published_at: "2026-06-30T11:00:00Z",
            published_version: 2,
            updated_at: "2026-06-30T11:00:00Z",
          },
        ],
      },
      meta: { total_count: 1 },
    }),
  ]);
  t.after(fetchMock.restore);

  const catalog = await ocrPipelinesClient.listBlockCatalog();
  const pipelines = await ocrPipelinesClient.listPipelines();

  assert.equal(
    catalog.data.blocks[0]?.implementationId,
    "document.preflight.prepare",
  );
  assert.equal(catalog.data.blocks[0]?.allowedFailurePolicies[0], "required");
  assert.equal(pipelines.data.pipelines[0]?.publishedVersion, 2);
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/admin/ocr/pipeline-blocks",
  );
  assert.equal(fetchMock.calls[1]?.input, "/api/docmind/admin/ocr/pipelines");
});

test("OCR pipeline client sends CSRF protected create and draft update payloads", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(detailEnvelope(), { status: 201 }),
    jsonResponse(detailEnvelope()),
  ]);
  t.after(fetchMock.restore);

  await ocrPipelinesClient.createPipeline(
    {
      description: "Draft pipeline",
      name: "Default OCR",
      steps: [
        {
          config: {},
          displayName: "Document preflight",
          enabled: true,
          failurePolicy: "required",
          implementationId: "document.preflight.prepare",
          stepId: "preflight",
        },
      ],
    },
    { csrfToken: "raw-csrf-token" },
  );
  await ocrPipelinesClient.updateDraft(
    PIPELINE_ID,
    {
      description: null,
      name: "Updated OCR",
      steps: [],
    },
    { csrfToken: "raw-csrf-token" },
  );

  assert.equal(fetchMock.calls[0]?.init.method, "POST");
  assert.equal(fetchMock.calls[1]?.init.method, "PATCH");
  assert.equal(
    new Headers(fetchMock.calls[0]?.init.headers).get("X-CSRF-Token"),
    "raw-csrf-token",
  );
  assert.deepEqual(JSON.parse(String(fetchMock.calls[0]?.init.body)), {
    description: "Draft pipeline",
    kind: "linear",
    name: "Default OCR",
    schema_version: 1,
    steps: [
      {
        config: {},
        display_name: "Document preflight",
        enabled: true,
        failure_policy: "required",
        implementation_id: "document.preflight.prepare",
        step_id: "preflight",
      },
    ],
  });
  assert.deepEqual(JSON.parse(String(fetchMock.calls[1]?.init.body)), {
    description: null,
    kind: "linear",
    name: "Updated OCR",
    schema_version: 1,
    steps: [],
  });
});

test("OCR pipeline client maps validation and lifecycle actions", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        catalog_hash: "hash",
        catalog_version: "ocr-pipeline-blocks-v1",
        compiled_snapshot: null,
        diagnostics: [
          {
            code: "MISSING_REQUIRED_STAGE",
            message: "OCR stage is required.",
            path: "steps",
            severity: "error",
            step_id: null,
          },
        ],
        valid: false,
      },
      meta: {},
    }),
    jsonResponse(detailEnvelope()),
    jsonResponse({ data: { deleted: true, id: PIPELINE_ID }, meta: {} }),
  ]);
  t.after(fetchMock.restore);

  const validation = await ocrPipelinesClient.validatePipeline(PIPELINE_ID, {
    csrfToken: "raw-csrf-token",
  });
  const archived = await ocrPipelinesClient.archivePipeline(PIPELINE_ID, {
    csrfToken: "raw-csrf-token",
  });
  const deleted = await ocrPipelinesClient.deletePipeline(PIPELINE_ID, {
    csrfToken: "raw-csrf-token",
  });

  assert.equal(validation.data.valid, false);
  assert.equal(validation.data.diagnostics[0]?.code, "MISSING_REQUIRED_STAGE");
  assert.equal(archived.data.id, PIPELINE_ID);
  assert.equal(deleted.deleted, true);
  assert.equal(
    fetchMock.calls[1]?.input,
    `/api/docmind/admin/ocr/pipelines/${PIPELINE_ID}/archive`,
  );
});

test("OCR pipeline client maps validation details from publish errors", () => {
  const validation = mapValidationErrorDetails({
    compiled_snapshot: { provider: "internal" },
    diagnostics: [
      {
        code: "PUBLISH_REVALIDATION_FAILED",
        message: "Publish revalidation failed.",
        path: "steps[0].config.model_id",
        severity: "error",
        step_id: "preflight",
      },
    ],
    pipeline_id: PIPELINE_ID,
  });

  assert.equal(validation?.valid, false);
  assert.equal(validation?.catalogHash, null);
  assert.equal(validation?.diagnostics[0]?.code, "PUBLISH_REVALIDATION_FAILED");
  assert.equal("compiledSnapshot" in (validation ?? {}), false);
});

function catalogEnvelope() {
  return {
    data: {
      blocks: [
        {
          allowed_failure_policies: ["required"],
          category: "preparation",
          config_schema: {},
          default_config: {},
          description: "Prepares documents.",
          disabled_reason: null,
          display_name: "Document preflight",
          implementation_id: "document.preflight.prepare",
          produces: ["document.preflight.result"],
          requires: [],
          status: "available",
          step_type: "preflight",
          ui_hints: { summary: "Required first step." },
          version: "1",
        },
      ],
      catalog_hash: "hash",
      catalog_version: "ocr-pipeline-blocks-v1",
    },
    meta: {},
  };
}

function detailEnvelope() {
  return {
    data: {
      archived_at: null,
      catalog_hash: null,
      catalog_version: null,
      compiled_snapshot: null,
      created_at: "2026-06-30T10:00:00Z",
      draft: {
        description: "Draft pipeline",
        kind: "linear",
        name: "Default OCR",
        schema_version: 1,
        steps: [],
      },
      id: PIPELINE_ID,
      is_default: false,
      last_validation: null,
      lifecycle: "draft",
      published_at: null,
      published_definition: null,
      published_version: null,
      updated_at: "2026-06-30T10:00:00Z",
    },
    meta: {},
  };
}
