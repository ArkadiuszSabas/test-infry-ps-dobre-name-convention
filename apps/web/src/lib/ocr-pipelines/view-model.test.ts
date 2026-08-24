import assert from "node:assert/strict";
import test from "node:test";

import type {
  OcrPipelineDetail,
  OcrPipelineValidation,
  OcrPipelineStep,
  OcrPipelineSummary,
} from "./types";
import {
  canEditOcrPipelineDetail,
  canEditOcrPipelineSummary,
  canPublishOcrPipeline,
  diagnosticBusinessMessageKey,
  detailHasUnpublishedDraftChanges,
  filterOcrPipelines,
  hasPublishReadyValidation,
  pipelineDefinitionForView,
  pipelineDisplayDefinitionState,
  pipelineHasUnpublishedDraftChanges,
  selectedVisiblePipelineId,
} from "./view-model";

test("filters OCR pipelines by lifecycle", () => {
  const pipelines: OcrPipelineSummary[] = [
    summary("draft-1", "Draft", "draft"),
    summary("published-1", "Published", "published"),
    summary("archived-1", "Archived", "archived"),
  ];

  assert.deepEqual(
    filterOcrPipelines(pipelines, "published").map((pipeline) => pipeline.id),
    ["published-1"],
  );
  assert.equal(filterOcrPipelines(pipelines, "all").length, 3);
});

test("keeps selected pipeline only when it is visible in the active filter", () => {
  const pipelines: OcrPipelineSummary[] = [
    summary("draft-1", "Draft", "draft"),
    summary("published-1", "Published", "published"),
  ];

  assert.equal(
    selectedVisiblePipelineId(pipelines, "published-1"),
    "published-1",
  );
  assert.equal(
    selectedVisiblePipelineId([pipelines[0]], "published-1"),
    "draft-1",
  );
  assert.equal(selectedVisiblePipelineId([], "published-1"), null);
});

test("allows publishing only a valid draft without blocking diagnostics", () => {
  assert.equal(canPublishOcrPipeline(detail({ lastValidation: null })), false);
  assert.equal(
    canPublishOcrPipeline(
      detail({ draft: null, lastValidation: validValidation() }),
    ),
    false,
  );
  assert.equal(
    canPublishOcrPipeline(
      detail({
        lastValidation: validValidation([
          {
            code: "BLOCKING",
            message: "Blocks publish.",
            path: null,
            severity: "error",
            stepId: null,
          },
        ]),
      }),
    ),
    false,
  );
  assert.equal(
    canPublishOcrPipeline(detail({ lastValidation: validValidation() })),
    true,
  );
  assert.equal(
    hasPublishReadyValidation(detail({ lastValidation: validValidation() })),
    true,
  );
});

test("maps technical validation diagnostics to business message keys", () => {
  assert.equal(
    diagnosticBusinessMessageKey({
      code: "DUPLICATE_ARTIFACT_PRODUCER",
      severity: "error",
    }),
    "duplicateArtifactProducer",
  );
  assert.equal(
    diagnosticBusinessMessageKey({
      code: "PIPELINE_STEPS_REQUIRED",
      severity: "error",
    }),
    "pipelineStepsRequired",
  );
  assert.equal(
    diagnosticBusinessMessageKey({
      code: "REQUIRED_STEP_TYPE_MISSING",
      severity: "error",
    }),
    "requiredStepTypeMissing",
  );
  assert.equal(
    diagnosticBusinessMessageKey({
      code: "UNKNOWN_BACKEND_CODE",
      severity: "warning",
    }),
    "genericWarning",
  );
  assert.equal(
    diagnosticBusinessMessageKey({
      code: "UNKNOWN_BACKEND_CODE",
      severity: "error",
    }),
    "genericError",
  );
});

test("allows editing draft and published pipelines while blocking archived details", () => {
  assert.equal(
    canEditOcrPipelineSummary(summary("published-1", "Published", "published")),
    true,
  );
  assert.equal(
    canEditOcrPipelineSummary({
      ...summary("archived-1", "Archived", "archived"),
      hasDraft: false,
    }),
    false,
  );
  assert.equal(
    canEditOcrPipelineDetail(
      detail({
        draft: null,
        lifecycle: "published",
        publishedDefinition: definition("Published definition"),
      }),
    ),
    true,
  );
  assert.equal(
    canEditOcrPipelineDetail(
      detail({
        lifecycle: "archived",
        publishedDefinition: definition("Archived definition"),
      }),
    ),
    false,
  );
});

test("labels draft and published display state distinctly", () => {
  const publishedWithDraft = detail({
    lifecycle: "published",
    publishedDefinition: definition("Published definition"),
  });
  const publishedOnly = detail({
    draft: null,
    lifecycle: "published",
    publishedDefinition: definition("Published definition"),
  });

  assert.equal(pipelineDisplayDefinitionState(publishedWithDraft), "draft");
  assert.equal(pipelineDisplayDefinitionState(publishedOnly), "published");
  assert.equal(detailHasUnpublishedDraftChanges(publishedWithDraft), true);
  assert.equal(
    pipelineHasUnpublishedDraftChanges({
      hasDraft: true,
      lifecycle: "published",
    }),
    true,
  );
});

test("returns the requested definition for a published pipeline with a draft", () => {
  const publishedWithDraft = detail({
    draft: definition("Draft definition"),
    lifecycle: "published",
    publishedDefinition: definition("Published definition"),
  });

  assert.equal(
    pipelineDefinitionForView(publishedWithDraft, "draft")?.name,
    "Draft definition",
  );
  assert.equal(
    pipelineDefinitionForView(publishedWithDraft, "published")?.name,
    "Published definition",
  );
});

function summary(
  id: string,
  name: string,
  lifecycle: OcrPipelineSummary["lifecycle"],
): OcrPipelineSummary {
  return {
    archivedAt: null,
    createdAt: "2026-06-30T10:00:00Z",
    description: null,
    hasDraft: lifecycle === "draft",
    id,
    isDefault: false,
    lastValidationValid: null,
    lifecycle,
    name,
    publishedAt: lifecycle === "published" ? "2026-06-30T11:00:00Z" : null,
    publishedVersion: lifecycle === "published" ? 1 : null,
    updatedAt: "2026-06-30T11:00:00Z",
  };
}

function step(stepId: string): OcrPipelineStep {
  return {
    config: {},
    displayName: stepId,
    enabled: true,
    failurePolicy: "required",
    implementationId: `document.${stepId}`,
    stepId,
  };
}

function definition(name: string): OcrPipelineDetail["publishedDefinition"] {
  return {
    description: null,
    kind: "linear",
    name,
    schemaVersion: 1,
    steps: [step("preflight")],
  };
}

function detail(overrides: Partial<OcrPipelineDetail> = {}): OcrPipelineDetail {
  return {
    archivedAt: null,
    catalogHash: "catalog-hash",
    catalogVersion: "catalog-version",
    createdAt: "2026-06-30T10:00:00Z",
    draft: definition("Draft"),
    id: "pipeline-1",
    isDefault: false,
    lastValidation: null,
    lifecycle: "draft",
    publishedAt: null,
    publishedDefinition: null,
    publishedVersion: null,
    updatedAt: "2026-06-30T11:00:00Z",
    ...overrides,
  };
}

function validValidation(
  diagnostics: OcrPipelineValidation["diagnostics"] = [],
): OcrPipelineValidation {
  return {
    catalogHash: "catalog-hash",
    catalogVersion: "catalog-version",
    diagnostics,
    valid: diagnostics.every((diagnostic) => diagnostic.severity !== "error"),
  };
}
