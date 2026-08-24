import assert from "node:assert/strict";
import test from "node:test";

import { authQueryKeys, currentActorQueryOptions } from "./query-options";

test("auth query helpers expose stable current actor keys", () => {
  assert.deepEqual(authQueryKeys.all, ["auth"]);
  assert.deepEqual(authQueryKeys.currentActor(), ["auth", "current-actor"]);
});

test("current actor query options keep auth resolution deterministic", () => {
  const options = currentActorQueryOptions();

  assert.deepEqual(options.queryKey, ["auth", "current-actor"]);
  assert.equal(options.refetchOnWindowFocus, true);
  assert.equal(options.retry, false);
  assert.equal(options.staleTime, 0);
  assert.equal(typeof options.queryFn, "function");
});
