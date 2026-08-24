import assert from "node:assert/strict";
import test from "node:test";

import type {
  OcrPipelineDiagnostic,
  OcrPipelineStep,
  OcrPipelineSummary,
} from "./types";
import {
  getDiagnosticTarget,
  getDiagnosticsForStep,
  getOcrPipelineRoutingStatus,
  getPipelineLevelDiagnostics,
  mostSevereDiagnostic,
} from "./diagnostics-view-model";

test("summarizes OCR pipeline routing readiness from published defaults", () => {
  assert.equal(getOcrPipelineRoutingStatus([]), "noPipelines");
  assert.equal(
    getOcrPipelineRoutingStatus([summary("draft", "draft", false)]),
    "noPublished",
  );
  assert.equal(
    getOcrPipelineRoutingStatus([summary("published", "published", false)]),
    "noDefault",
  );
  assert.equal(
    getOcrPipelineRoutingStatus([summary("default", "published", true)]),
    "ready",
  );
});

test("maps diagnostics to step and control targets from step id and path", () => {
  const steps = [step("preflight"), step("ocr")];
  const stepDiagnostic: OcrPipelineDiagnostic = {
    code: "MODEL_REQUIRED",
    message: "Select an OCR model.",
    path: "steps[1].config.model_id",
    severity: "error",
    stepId: "ocr",
  };
  const pipelineDiagnostic: OcrPipelineDiagnostic = {
    code: "MISSING_REQUIRED_STAGE",
    message: "OCR stage is required.",
    path: "steps",
    severity: "warning",
    stepId: null,
  };

  const target = getDiagnosticTarget(stepDiagnostic, steps);

  assert.equal(target.stepIndex, 1);
  assert.equal(target.step?.displayName, "ocr");
  assert.equal(target.fieldPath, "config.model_id");
  assert.deepEqual(getDiagnosticsForStep([stepDiagnostic], steps, 1), [
    stepDiagnostic,
  ]);
  assert.deepEqual(
    getPipelineLevelDiagnostics([stepDiagnostic, pipelineDiagnostic], steps),
    [pipelineDiagnostic],
  );
  assert.equal(mostSevereDiagnostic([pipelineDiagnostic]), "warning");
  assert.equal(
    mostSevereDiagnostic([pipelineDiagnostic, stepDiagnostic]),
    "error",
  );
});

test("uses diagnostic path index before duplicate step id fallback", () => {
  const steps = [step("duplicate"), step("duplicate")];
  const target = getDiagnosticTarget(
    {
      code: "MODEL_REQUIRED",
      message: "Select an OCR model.",
      path: "steps[1].config.model_id",
      severity: "error",
      stepId: "duplicate",
    },
    steps,
  );

  assert.equal(target.stepIndex, 1);
  assert.equal(target.fieldPath, "config.model_id");
});

function summary(
  id: string,
  lifecycle: OcrPipelineSummary["lifecycle"],
  isDefault: boolean,
): OcrPipelineSummary {
  return {
    archivedAt: null,
    createdAt: "2026-06-30T10:00:00Z",
    description: null,
    hasDraft: lifecycle === "draft",
    id,
    isDefault,
    lastValidationValid: null,
    lifecycle,
    name: id,
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
