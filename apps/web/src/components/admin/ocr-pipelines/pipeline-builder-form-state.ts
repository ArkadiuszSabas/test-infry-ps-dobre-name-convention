import type {
  OcrPipelineDetail,
  OcrPipelineStep,
} from "@/lib/ocr-pipelines/types";
import {
  cloneOcrPipelineSteps,
  duplicatePipelineName,
} from "@/lib/ocr-pipelines/view-model";

export type PipelineBuilderTarget =
  | { kind: "create" }
  | { detail: OcrPipelineDetail; kind: "duplicate" }
  | { detail: OcrPipelineDetail; kind: "edit" };

export interface PipelineBuilderFormState {
  description: string;
  name: string;
  steps: OcrPipelineStep[];
}

export function getInitialFormState(
  target: PipelineBuilderTarget,
  options: {
    duplicateNameSuffix: string;
    existingPipelineNames: readonly string[];
  },
): PipelineBuilderFormState {
  if (target.kind === "create") {
    return {
      description: "",
      name: "",
      steps: [],
    };
  }

  const definition = target.detail.draft ?? target.detail.publishedDefinition;

  return {
    description: definition?.description ?? "",
    name:
      target.kind === "duplicate" && definition?.name
        ? duplicatePipelineName(definition.name, {
            existingNames: options.existingPipelineNames,
            suffix: options.duplicateNameSuffix,
          })
        : (definition?.name ?? ""),
    steps: definition ? cloneOcrPipelineSteps(definition.steps) : [],
  };
}
