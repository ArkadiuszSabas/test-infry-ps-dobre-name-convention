import assert from "node:assert/strict";
import test from "node:test";

import { adminOcrRunListQueryOptions } from "./query-options";

test("admin OCR polling is enabled only for active runs", () => {
  const base = { limit: 25, offset: 0 } as const;
  const active = adminOcrRunListQueryOptions({ ...base, view: "active" });
  const history = adminOcrRunListQueryOptions({ ...base, view: "history" });

  assert.equal(active.refetchInterval, 5_000);
  assert.equal(active.refetchIntervalInBackground, false);
  assert.equal(history.refetchInterval, false);
});
