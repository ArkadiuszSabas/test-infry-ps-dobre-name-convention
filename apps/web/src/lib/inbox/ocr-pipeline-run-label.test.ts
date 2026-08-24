import assert from "node:assert/strict";
import test from "node:test";

import { getOcrPipelineRunLabel } from "./ocr-pipeline-run-label";

test("uses the pipeline name and version when the API provides a name", () => {
  assert.deepEqual(
    getOcrPipelineRunLabel({
      pipelineId: "77777777-7777-7777-7777-777777777777",
      pipelineName: "Invoice OCR",
      pipelineVersion: 2,
    }),
    {
      key: "pipeline",
      values: { name: "Invoice OCR", version: 2 },
    },
  );
});

test("uses the pipeline identifier fallback when the API has no name", () => {
  assert.deepEqual(
    getOcrPipelineRunLabel({
      pipelineId: "77777777-7777-7777-7777-777777777777",
      pipelineName: null,
      pipelineVersion: 2,
    }),
    {
      key: "pipelineFallback",
      values: {
        id: "77777777-7777-7777-7777-777777777777",
        version: 2,
      },
    },
  );
});
