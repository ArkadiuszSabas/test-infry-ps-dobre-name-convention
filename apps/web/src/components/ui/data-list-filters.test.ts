import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { formatDataListFilterOptionLabel } from "./data-list-filters";

describe("data list filters", () => {
  it("formats plain option labels", () => {
    assert.equal(
      formatDataListFilterOptionLabel({ label: "Aktywne" }),
      "Aktywne",
    );
  });

  it("appends option counts when provided", () => {
    assert.equal(
      formatDataListFilterOptionLabel({ count: 3, label: "Aktywne" }),
      "Aktywne (3)",
    );
  });
});
