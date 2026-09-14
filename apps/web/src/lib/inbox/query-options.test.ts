import assert from "node:assert/strict";
import test from "node:test";

import {
  documentOcrPipelineRunsQueryOptions,
  inboxDocumentsQueryOptions,
  inboxQueryKeys,
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

test("document list query key includes every backend-owned criterion", () => {
  const options = inboxDocumentsQueryOptions({
    archived: true,
    documentTypeId: "type-1",
    limit: 50,
    offset: 100,
    search: "invoice",
    sortBy: "name",
    sortDirection: "asc",
    status: "received",
  });

  assert.deepEqual(options.queryKey, [
    "inbox",
    "documents",
    "list",
    {
      archived: true,
      documentTypeId: "type-1",
      limit: 50,
      offset: 100,
      search: "invoice",
      sortBy: "name",
      sortDirection: "asc",
      status: "received",
    },
  ]);
});

test("document list and context prefixes invalidate every query variant", () => {
  const query = {
    archived: true,
    limit: 50,
    offset: 100,
    sortBy: "name" as const,
    sortDirection: "asc" as const,
  };

  assert.deepEqual(inboxQueryKeys.documentLists(), [
    "inbox",
    "documents",
    "list",
  ]);
  assert.deepEqual(inboxQueryKeys.documentContexts(), [
    "inbox",
    "documents",
    "context",
  ]);
  assert.deepEqual(inboxQueryKeys.documentContext("document-1", query), [
    "inbox",
    "documents",
    "context",
    "document-1",
    query,
  ]);
});
