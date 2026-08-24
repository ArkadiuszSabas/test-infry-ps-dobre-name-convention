import type { OcrPipelineRun } from "./ocr-pipeline-runs-types";

export function getOcrPipelineRunLabel(
  run: Pick<OcrPipelineRun, "pipelineId" | "pipelineName" | "pipelineVersion">,
): {
  key: "pipeline" | "pipelineFallback";
  values: Record<string, string | number>;
} {
  if (run.pipelineName) {
    return {
      key: "pipeline",
      values: { name: run.pipelineName, version: run.pipelineVersion },
    };
  }

  return {
    key: "pipelineFallback",
    values: { id: run.pipelineId, version: run.pipelineVersion },
  };
}
