import assert from "node:assert/strict";
import test from "node:test";

import { QueryClient } from "@tanstack/react-query";

import { inboxQueryKeys } from "@/lib/inbox/query-options";

import { authQueryKeys } from "./query-options";
import { clearBrowserSessionQueryCache } from "./session-cache";

test("browser session cache clearing removes auth and product query data", () => {
  const queryClient = new QueryClient();
  queryClient.setQueryData(authQueryKeys.currentActor(), {
    email: "first.user@example.test",
  });
  queryClient.setQueryData(inboxQueryKeys.documentList(), {
    pages: [
      {
        data: {
          documents: [{ original_filename: "first-user-invoice.pdf" }],
        },
      },
    ],
    pageParams: [0],
  });

  clearBrowserSessionQueryCache(queryClient);

  assert.equal(
    queryClient.getQueryData(authQueryKeys.currentActor()),
    undefined,
  );
  assert.equal(
    queryClient.getQueryData(inboxQueryKeys.documentList()),
    undefined,
  );
});

test("browser session cache clearing removes previous account product data before seeding the new actor", () => {
  const queryClient = new QueryClient();
  const nextActor = {
    email: "second.user@example.test",
    permissions: ["documents.read"],
    roles: ["reviewer"],
    user_id: "second-user",
  };

  queryClient.setQueryData(authQueryKeys.currentActor(), {
    email: "first.user@example.test",
    permissions: ["admin.settings.manage", "documents.read"],
    roles: ["admin"],
    user_id: "first-user",
  });
  queryClient.setQueryData(inboxQueryKeys.documentList(), {
    pages: [
      {
        data: {
          documents: [{ original_filename: "first-user-contract.pdf" }],
        },
      },
    ],
    pageParams: [0],
  });

  clearBrowserSessionQueryCache(queryClient);
  queryClient.setQueryData(authQueryKeys.currentActor(), nextActor);

  assert.equal(
    queryClient.getQueryData(inboxQueryKeys.documentList()),
    undefined,
  );
  assert.deepEqual(
    queryClient.getQueryData(authQueryKeys.currentActor()),
    nextActor,
  );
});
