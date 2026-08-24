import assert from "node:assert/strict";
import test from "node:test";

import { ocrPipelineQueryKeys } from "./query-options";

test("OCR pipeline detail keys share a prefix for bulk invalidation", () => {
  assert.deepEqual(ocrPipelineQueryKeys.details(), [
    "admin",
    "ocr-pipelines",
    "pipelines",
    "detail",
  ]);
  assert.deepEqual(ocrPipelineQueryKeys.detail("pipeline-1"), [
    ...ocrPipelineQueryKeys.details(),
    "pipeline-1",
  ]);
});
