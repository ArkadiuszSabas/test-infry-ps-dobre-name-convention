import assert from "node:assert/strict";
import test from "node:test";

import { installFetchMock, jsonResponse } from "@/lib/api/test-helpers";

import { approvalSettingsClient } from "./api";

test("reads and updates document approval settings", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        required_approvals: 2,
        schema_version: 1,
        updated_at: null,
      },
      meta: {},
    }),
    jsonResponse({
      data: {
        required_approvals: 1,
        schema_version: 1,
        updated_at: "2026-07-31T10:00:00+00:00",
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  const loaded = await approvalSettingsClient.getSettings();
  const updated = await approvalSettingsClient.updateSettings(1, null, {
    csrfToken: "csrf-token",
  });

  assert.equal(loaded.requiredApprovals, 2);
  assert.equal(updated.requiredApprovals, 1);
  const request = fetchMock.calls[1];
  assert.equal(request?.init.method, "PUT");
  assert.equal(
    new Headers(request?.init.headers).get("X-CSRF-Token"),
    "csrf-token",
  );
  assert.deepEqual(JSON.parse(String(request?.init.body)), {
    expected_updated_at: null,
    required_approvals: 1,
  });
});
