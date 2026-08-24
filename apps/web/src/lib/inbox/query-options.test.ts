import assert from "node:assert/strict";
import test from "node:test";

import {
  documentOcrPipelineRunsQueryOptions,
  ocrPipelineRunResultQueryOptions,
} from "./query-options";

test("OCR history query leaves polling to its page-level owner", () => {
  const activeOptions = documentOcrPipelineRunsQueryOptions("document-1");
  const passiveOptions = documentOcrPipelineRunsQueryOptions(
    "document-1",
    false,
  );

  assert.equal(activeOptions.enabled, true);
  assert.equal(passiveOptions.enabled, false);
  assert.equal(activeOptions.refetchInterval, undefined);
  assert.equal(passiveOptions.refetchInterval, undefined);
});

test("OCR result query performs one terminal fetch without polling", () => {
  const options = ocrPipelineRunResultQueryOptions("run-1", true);

  assert.equal(options.enabled, true);
  assert.equal(options.refetchInterval, undefined);
});
