import assert from "node:assert/strict";
import test from "node:test";

import {
  parseAttributeMappings,
  serializeAttributeMappings,
} from "@/lib/connector-configurations/attribute-mappings";

test("serializes attribute mappings without changing editable values or order", () => {
  assert.equal(
    serializeAttributeMappings([
      {
        attribute_definition_id: " attribute-1 ",
        column: " Title ",
      },
      {
        attribute_definition_id: "attribute-2",
        column: "Numer_Klienta",
      },
    ]),
    '[{"attribute_definition_id":" attribute-1 ","column":" Title "},' +
      '{"attribute_definition_id":"attribute-2","column":"Numer_Klienta"}]',
  );
});

test("parses only complete mapping objects", () => {
  assert.deepEqual(
    parseAttributeMappings(
      '[{"column":"Title","attribute_definition_id":"attribute-1"},' +
        '{"column":42,"attribute_definition_id":"attribute-2"}]',
    ),
    [{ attribute_definition_id: "attribute-1", column: "Title" }],
  );
  assert.deepEqual(parseAttributeMappings("not-json"), []);
});
