import type {
  OcrPipelineDiagnostic,
  OcrPipelineDiagnosticSeverity,
  OcrPipelineStep,
  OcrPipelineSummary,
} from "./types";

export type OcrPipelineRoutingStatus =
  | "noDefault"
  | "noPipelines"
  | "noPublished"
  | "ready";

export interface OcrPipelineDiagnosticTarget {
  fieldPath: string | null;
  step: OcrPipelineStep | null;
  stepIndex: number | null;
}

export function getOcrPipelineRoutingStatus(
  pipelines: readonly OcrPipelineSummary[],
): OcrPipelineRoutingStatus {
  if (pipelines.length === 0) {
    return "noPipelines";
  }

  const publishedPipelines = pipelines.filter(
    (pipeline) => pipeline.lifecycle === "published",
  );

  if (publishedPipelines.length === 0) {
    return "noPublished";
  }

  if (!publishedPipelines.some((pipeline) => pipeline.isDefault)) {
    return "noDefault";
  }

  return "ready";
}

export function getDiagnosticTarget(
  diagnostic: OcrPipelineDiagnostic,
  steps: readonly OcrPipelineStep[],
): OcrPipelineDiagnosticTarget {
  const pathTarget = parseStepPath(diagnostic.path);
  const stepIdTarget =
    diagnostic.stepId === null
      ? null
      : steps.findIndex((step) => step.stepId === diagnostic.stepId);
  const stepIndex =
    pathTarget?.stepIndex ??
    (stepIdTarget !== null && stepIdTarget >= 0 ? stepIdTarget : null);
  const step = stepIndex === null ? null : (steps[stepIndex] ?? null);

  return {
    fieldPath: pathTarget?.fieldPath ?? null,
    step,
    stepIndex: step ? stepIndex : null,
  };
}

export function getDiagnosticsForStep(
  diagnostics: readonly OcrPipelineDiagnostic[],
  steps: readonly OcrPipelineStep[],
  stepIndex: number,
): OcrPipelineDiagnostic[] {
  return diagnostics.filter(
    (diagnostic) =>
      getDiagnosticTarget(diagnostic, steps).stepIndex === stepIndex,
  );
}

export function getPipelineLevelDiagnostics(
  diagnostics: readonly OcrPipelineDiagnostic[],
  steps: readonly OcrPipelineStep[],
): OcrPipelineDiagnostic[] {
  return diagnostics.filter(
    (diagnostic) => getDiagnosticTarget(diagnostic, steps).stepIndex === null,
  );
}

export function mostSevereDiagnostic(
  diagnostics: readonly OcrPipelineDiagnostic[],
): OcrPipelineDiagnosticSeverity | null {
  if (diagnostics.some((diagnostic) => diagnostic.severity === "error")) {
    return "error";
  }

  if (diagnostics.some((diagnostic) => diagnostic.severity === "warning")) {
    return "warning";
  }

  if (diagnostics.some((diagnostic) => diagnostic.severity === "info")) {
    return "info";
  }

  return null;
}

function parseStepPath(
  path: string | null,
): { fieldPath: string | null; stepIndex: number } | null {
  if (!path) {
    return null;
  }

  const match = /^steps\[(\d+)\](?:\.(.+))?$/.exec(path);

  if (!match?.[1]) {
    return null;
  }

  return {
    fieldPath: match[2] ?? null,
    stepIndex: Number.parseInt(match[1], 10),
  };
}
