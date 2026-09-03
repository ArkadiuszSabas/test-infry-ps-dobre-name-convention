import assert from "node:assert/strict";
import test from "node:test";

import { getListPaginationRange } from "./list-pagination-range";

test("page range does not invent an item for an empty out-of-range page", () => {
  assert.deepEqual(
    getListPaginationRange({ offset: 50, returnedCount: 0, total: 23 }),
    { first: 0, last: 0, total: 23 },
  );
});
