import type { OcrPipelineStep } from "./types";
import { sanitizeNormalizationStepConfig } from "./builder-view-model";

export const OCR_PIPELINE_NAME_MAX_LENGTH = 200;
export const OCR_PIPELINE_STEP_DISPLAY_NAME_MAX_LENGTH = 120;

export function duplicatePipelineName(
  name: string,
  options: {
    existingNames?: readonly string[];
    suffix?: string;
  } = {},
): string {
  const normalized = name.trim();
  const suffix = options.suffix?.trim() || "copy";

  if (!normalized) {
    return "";
  }

  const existingNames = new Set(
    (options.existingNames ?? []).map((existingName) =>
      existingName.trim().toLocaleLowerCase(),
    ),
  );
  const baseCandidate = duplicateNameCandidate(normalized, suffix);

  if (!existingNames.has(baseCandidate.toLocaleLowerCase())) {
    return baseCandidate;
  }

  for (let index = 2; index < 100; index += 1) {
    const candidate = duplicateNameCandidate(normalized, `${suffix} ${index}`);

    if (!existingNames.has(candidate.toLocaleLowerCase())) {
      return candidate;
    }
  }

  return duplicateNameCandidate(normalized, `${suffix} ${Date.now()}`);
}

export function cloneOcrPipelineSteps(
  steps: readonly OcrPipelineStep[],
): OcrPipelineStep[] {
  return steps.map((step) => ({
    ...step,
    config: structuredClone(step.config),
  }));
}

export function prepareStepsForSubmit(
  steps: readonly OcrPipelineStep[],
  visibleAttributeExternalIds: readonly string[],
): OcrPipelineStep[] {
  return steps.map((step) =>
    sanitizeNormalizationStepConfig(
      {
        ...step,
        displayName: step.displayName.trim(),
      },
      visibleAttributeExternalIds,
    ),
  );
}

function duplicateNameCandidate(name: string, suffix: string): string {
  const normalizedSuffix = suffix.trim();
  const suffixPart = normalizedSuffix ? ` ${normalizedSuffix}` : "";
  const baseLength = Math.max(
    0,
    OCR_PIPELINE_NAME_MAX_LENGTH - suffixPart.length,
  );

  return `${name.slice(0, baseLength).trimEnd()}${suffixPart}`.slice(
    0,
    OCR_PIPELINE_NAME_MAX_LENGTH,
  );
}
