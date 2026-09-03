import assert from "node:assert/strict";
import test from "node:test";

import { listQueryOptions } from "./list-query-options";

test("listQueryOptions keys every criterion, forwards cancellation and retains a prior page", async () => {
  const query = { limit: 10, offset: 20, status: "active" };
  let receivedSignal: AbortSignal | undefined;
  const options = listQueryOptions({
    query,
    queryKey: ["examples"],
    request: async (_query, signal) => {
      receivedSignal = signal;
      return { items: [] };
    },
  });
  const controller = new AbortController();

  assert.deepEqual(options.queryKey, ["examples", query]);
  assert.equal(typeof options.placeholderData, "function");
  await options.queryFn?.({
    client: undefined as never,
    meta: undefined,
    queryKey: options.queryKey,
    signal: controller.signal,
  });
  assert.equal(receivedSignal, controller.signal);
});
