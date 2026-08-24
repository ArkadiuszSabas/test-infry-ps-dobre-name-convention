import type { PipelineBuilderTarget } from "@/components/admin/ocr-pipelines/pipeline-builder-form-state";
import { isApiError } from "@/lib/api/errors";
import { mapValidationErrorDetails } from "@/lib/ocr-pipelines/api-mappers";
import type {
  CreateOcrPipelineInput,
  OcrPipelineValidation,
} from "@/lib/ocr-pipelines/types";

import type { OcrPipelineActionKind } from "./pipeline-list";

export type PendingActionKind = Exclude<
  OcrPipelineActionKind,
  "duplicate" | "edit" | "open"
>;

export interface PendingAction {
  kind: PendingActionKind;
  pipelineId: string;
  pipelineName: string;
}

export interface SaveVariables {
  input: CreateOcrPipelineInput;
  target: PipelineBuilderTarget;
}

export interface LatestValidation {
  pipelineId: string;
  validation: OcrPipelineValidation;
}

export interface PipelineActionError {
  error: unknown;
  pipelineId: string;
}

export function validationFromPublishError(
  error: unknown,
): OcrPipelineValidation | null {
  return isApiError(error) ? mapValidationErrorDetails(error.details) : null;
}
