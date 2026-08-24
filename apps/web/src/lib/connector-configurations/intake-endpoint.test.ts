import assert from "node:assert/strict";
import test from "node:test";

import { toAbsoluteConnectorEndpoint } from "./intake-endpoint";

test("connector endpoint uses the browser origin for a proxied API path", () => {
  assert.equal(
    toAbsoluteConnectorEndpoint(
      "/api/docmind/connectors/sample/intake",
      "https://test.docmind.example",
    ),
    "https://test.docmind.example/api/docmind/connectors/sample/intake",
  );
});

test("connector endpoint keeps a configured absolute API origin", () => {
  assert.equal(
    toAbsoluteConnectorEndpoint(
      "https://api.prod.docmind.example/connectors/sample/intake",
      "https://app.prod.docmind.example",
    ),
    "https://api.prod.docmind.example/connectors/sample/intake",
  );
});
