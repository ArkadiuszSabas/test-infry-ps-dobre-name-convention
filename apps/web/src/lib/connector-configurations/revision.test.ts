import assert from "node:assert/strict";
import test from "node:test";

import { expectedConnectorConfigurationRevision } from "./revision";

test("connector configuration edits retain the revision that was first edited", () => {
  assert.equal(
    expectedConnectorConfigurationRevision(
      "2026-07-21T10:00:00Z",
      "2026-07-21T10:01:00Z",
    ),
    "2026-07-21T10:00:00Z",
  );
});

test("connector configuration uses the current revision before an edit starts", () => {
  assert.equal(
    expectedConnectorConfigurationRevision(undefined, "2026-07-21T10:01:00Z"),
    "2026-07-21T10:01:00Z",
  );
});
