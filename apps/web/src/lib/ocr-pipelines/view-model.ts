import type {
  OcrPipelineDetail,
  OcrPipelineSummary,
  OcrPipelineValidation,
} from "./types";

export {
  cloneOcrPipelineSteps,
  duplicatePipelineName,
  OCR_PIPELINE_NAME_MAX_LENGTH,
  OCR_PIPELINE_STEP_DISPLAY_NAME_MAX_LENGTH,
  prepareStepsForSubmit,
} from "./builder-form-view-model";

export {
  configAttributes,
  configNumber,
  configString,
  configStringEnum,
  createStepFromBlock,
  getBlockSummary,
  groupBlocksByCategory,
  hasNormalizationStep,
  moveStep,
  OCR_PIPELINE_NORMALIZATION_STEP_ID,
  presetConfigKey,
  removeStepAt,
  sanitizeNormalizationStepConfig,
  selectablePipelineBlocks,
  updateStepAt,
  visibleNormalizationAttributes,
  withConfigValue,
  withDocumentTypeId,
  withNormalizationAttributes,
} from "./builder-view-model";

export const ocrPipelineLifecycleFilters = [
  "all",
  "draft",
  "published",
  "archived",
] as const;

export type OcrPipelineLifecycleFilter =
  (typeof ocrPipelineLifecycleFilters)[number];

export type OcrPipelineDisplayDefinitionState = "draft" | "none" | "published";

export type OcrPipelineDefinitionView = "draft" | "published";

export function isOcrPipelineLifecycleFilter(
  value: string,
): value is OcrPipelineLifecycleFilter {
  return ocrPipelineLifecycleFilters.some((filter) => filter === value);
}

export function filterOcrPipelines(
  pipelines: readonly OcrPipelineSummary[],
  filter: OcrPipelineLifecycleFilter,
): OcrPipelineSummary[] {
  if (filter === "all") {
    return [...pipelines];
  }

  return pipelines.filter((pipeline) => pipeline.lifecycle === filter);
}

export function selectedVisiblePipelineId(
  pipelines: readonly OcrPipelineSummary[],
  selectedPipelineId: string | null,
): string | null {
  if (
    selectedPipelineId &&
    pipelines.some((pipeline) => pipeline.id === selectedPipelineId)
  ) {
    return selectedPipelineId;
  }

  return pipelines[0]?.id ?? null;
}

export function getOcrPipelineFilterCount(
  pipelines: readonly OcrPipelineSummary[],
  filter: OcrPipelineLifecycleFilter,
): number {
  return filterOcrPipelines(pipelines, filter).length;
}

export function pipelineDisplayDefinition(detail: OcrPipelineDetail) {
  return detail.draft ?? detail.publishedDefinition;
}

export function pipelineDefinitionForView(
  detail: OcrPipelineDetail,
  view: OcrPipelineDefinitionView,
) {
  if (view === "published") {
    return detail.publishedDefinition;
  }

  return detail.draft;
}

export function pipelineDisplayDefinitionState(
  detail: OcrPipelineDetail,
): OcrPipelineDisplayDefinitionState {
  if (detail.draft) {
    return "draft";
  }

  return detail.publishedDefinition ? "published" : "none";
}

export function pipelineHasUnpublishedDraftChanges(
  pipeline: Pick<OcrPipelineSummary, "hasDraft" | "lifecycle">,
): boolean {
  return pipeline.lifecycle === "published" && pipeline.hasDraft;
}

export function detailHasUnpublishedDraftChanges(
  detail: Pick<OcrPipelineDetail, "draft" | "lifecycle">,
): boolean {
  return detail.lifecycle === "published" && Boolean(detail.draft);
}

export function hasBlockingDiagnostics(
  validation: OcrPipelineValidation | null,
): boolean {
  return Boolean(
    validation?.diagnostics.some(
      (diagnostic) => diagnostic.severity === "error",
    ),
  );
}

export function canPublishOcrPipeline(detail: OcrPipelineDetail): boolean {
  return Boolean(
    detail.draft &&
    detail.lastValidation?.valid === true &&
    !hasBlockingDiagnostics(detail.lastValidation),
  );
}

export function canEditOcrPipelineSummary(
  pipeline: OcrPipelineSummary,
): boolean {
  return (
    pipeline.lifecycle !== "archived" &&
    (pipeline.hasDraft || pipeline.lifecycle === "published")
  );
}

export function canEditOcrPipelineDetail(detail: OcrPipelineDetail): boolean {
  return Boolean(
    detail.lifecycle !== "archived" &&
    (detail.draft ?? detail.publishedDefinition),
  );
}

export function validationState(
  valid: boolean | null,
): "invalid" | "unknown" | "valid" {
  if (valid === true) {
    return "valid";
  }

  if (valid === false) {
    return "invalid";
  }

  return "unknown";
}

export type OcrPipelineDiagnosticMessageKey =
  | "duplicateArtifactProducer"
  | "pipelineStepsRequired"
  | "requiredStepTypeMissing"
  | "genericError"
  | "genericInfo"
  | "genericWarning";

export function diagnosticBusinessMessageKey(
  diagnostic: Pick<
    OcrPipelineValidation["diagnostics"][number],
    "code" | "severity"
  >,
): OcrPipelineDiagnosticMessageKey {
  if (diagnostic.code === "DUPLICATE_ARTIFACT_PRODUCER") {
    return "duplicateArtifactProducer";
  }

  if (diagnostic.code === "PIPELINE_STEPS_REQUIRED") {
    return "pipelineStepsRequired";
  }

  if (diagnostic.code === "REQUIRED_STEP_TYPE_MISSING") {
    return "requiredStepTypeMissing";
  }

  if (diagnostic.severity === "error") {
    return "genericError";
  }

  if (diagnostic.severity === "warning") {
    return "genericWarning";
  }

  return "genericInfo";
}

export function hasPublishReadyValidation(detail: OcrPipelineDetail): boolean {
  return Boolean(
    detail.draft &&
    detail.lastValidation?.valid === true &&
    !hasBlockingDiagnostics(detail.lastValidation),
  );
}
