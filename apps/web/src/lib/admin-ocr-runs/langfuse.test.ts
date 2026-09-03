import assert from "node:assert/strict";
import test from "node:test";

import { buildLangfuseProjectUrl, buildLangfuseSessionUrl } from "./langfuse";

test("Langfuse runtime settings select each environment's explicit project", () => {
  for (const projectId of [
    "dev-project-id",
    "sb1_project_id",
    "cmsypetq4000c2007ysnqvifp",
    "prd-project-id",
  ]) {
    assert.equal(
      buildLangfuseProjectUrl("https://langfuse.example.test/", projectId),
      `https://langfuse.example.test/project/${projectId}`,
    );
  }
});

test("Langfuse project URL builds an encoded OCR session deep link", () => {
  const projectUrl = buildLangfuseProjectUrl(
    "https://langfuse.example.test/",
    "cmsypetq4000c2007ysnqvifp",
  );
  assert.equal(
    buildLangfuseSessionUrl(projectUrl!, "run/unsafe"),
    "https://langfuse.example.test/project/cmsypetq4000c2007ysnqvifp/sessions/run%2Funsafe",
  );
});

test("Langfuse runtime settings reject unsafe or incomplete values", () => {
  assert.equal(
    buildLangfuseProjectUrl("javascript:alert(1)", "project-id"),
    null,
  );
  assert.equal(
    buildLangfuseProjectUrl("https://langfuse.test", undefined),
    null,
  );
  assert.equal(
    buildLangfuseProjectUrl("https://langfuse.test/path", "project-id"),
    null,
  );
  assert.equal(
    buildLangfuseProjectUrl(
      "https://langfuse.test?redirect=unsafe",
      "project-id",
    ),
    null,
  );
  assert.equal(
    buildLangfuseProjectUrl("https://langfuse.test", "../unsafe"),
    null,
  );
});
