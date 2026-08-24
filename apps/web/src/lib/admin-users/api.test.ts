import assert from "node:assert/strict";
import test from "node:test";

import { adminUsersClient } from "./api";

test("admin users client lists pending invitations", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        invitations: [invitationResponseBody()],
      },
      meta: {
        delivery_available: false,
        evaluated_at: "2026-06-11T12:10:00Z",
      },
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await adminUsersClient.listInvitations();

  assert.equal(result.data.invitations[0]?.email, "invited.user@example.com");
  assert.equal(fetchMock.calls[0]?.input, "/api/docmind/auth/invitations");
  assert.equal(fetchMock.calls[0]?.init.method, "GET");
});

test("admin users client manages users through CSRF protected routes", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        users: [managedUserResponseBody()],
      },
      meta: {
        evaluated_at: "2026-06-24T12:00:00Z",
        include_deleted: false,
        returned_count: 1,
        total_count: 1,
      },
    }),
    jsonResponse(
      {
        data: managedUserResponseBody({
          display_name: "Created User",
          email: "created.user@example.com",
        }),
        meta: {
          evaluated_at: "2026-06-24T12:01:00Z",
          revoked_sessions: 0,
        },
      },
      { status: 201 },
    ),
    jsonResponse({
      data: managedUserResponseBody({ status: "inactive" }),
      meta: {
        evaluated_at: "2026-06-24T12:02:00Z",
        revoked_sessions: 2,
      },
    }),
    jsonResponse({
      data: {
        deleted: true,
        id: "22222222-2222-2222-2222-222222222222",
      },
      meta: {
        evaluated_at: "2026-06-24T12:03:00Z",
        revoked_sessions: 3,
      },
    }),
    jsonResponse({
      data: {
        changed: true,
        id: "22222222-2222-2222-2222-222222222222",
      },
      meta: {
        evaluated_at: "2026-06-24T12:04:00Z",
        revoked_sessions: 4,
      },
    }),
  ]);
  t.after(fetchMock.restore);

  await adminUsersClient.listUsers();
  await adminUsersClient.createUser(
    {
      display_name: "Created User",
      login: "created.user@example.com",
      password: "temporary-secret",
      roles: ["viewer"],
      status: "active",
    },
    { csrfToken: "raw-csrf-token" },
  );
  await adminUsersClient.updateUser(
    "22222222-2222-2222-2222-222222222222",
    { status: "inactive" },
    { csrfToken: "raw-csrf-token" },
  );
  await adminUsersClient.deleteUser("22222222-2222-2222-2222-222222222222", {
    csrfToken: "raw-csrf-token",
  });
  await adminUsersClient.setUserPassword(
    "22222222-2222-2222-2222-222222222222",
    { new_password: "new-secret" },
    { csrfToken: "raw-csrf-token" },
  );

  assert.equal(fetchMock.calls[0]?.input, "/api/docmind/auth/users");
  assert.equal(fetchMock.calls[1]?.input, "/api/docmind/auth/users");
  assert.equal(
    fetchMock.calls[2]?.input,
    "/api/docmind/auth/users/22222222-2222-2222-2222-222222222222",
  );
  assert.equal(fetchMock.calls[3]?.init.method, "DELETE");
  assert.equal(
    fetchMock.calls[4]?.input,
    "/api/docmind/auth/users/22222222-2222-2222-2222-222222222222/password",
  );
  assert.deepEqual(JSON.parse(String(fetchMock.calls[1]?.init.body)), {
    display_name: "Created User",
    login: "created.user@example.com",
    password: "temporary-secret",
    roles: ["viewer"],
    status: "active",
  });
  assert.deepEqual(JSON.parse(String(fetchMock.calls[2]?.init.body)), {
    status: "inactive",
  });
  assert.deepEqual(JSON.parse(String(fetchMock.calls[4]?.init.body)), {
    new_password: "new-secret",
  });
  for (const call of fetchMock.calls.slice(1)) {
    assert.equal(
      new Headers(call.init.headers).get("X-CSRF-Token"),
      "raw-csrf-token",
    );
  }
});

test("admin users client sends CSRF protected invitation mutations", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(
      {
        data: invitationResponseBody({
          email: "reviewer@example.com",
          roles: ["viewer", "reviewer"],
        }),
        meta: {
          delivery_available: false,
          evaluated_at: "2026-06-11T12:10:00Z",
        },
      },
      { status: 201 },
    ),
    jsonResponse({
      data: invitationResponseBody({
        cancelled_at: "2026-06-11T12:20:00Z",
        cancelled_by_user_id: "11111111-1111-1111-1111-111111111111",
        status: "cancelled",
      }),
      meta: {
        delivery_available: false,
        evaluated_at: "2026-06-11T12:20:00Z",
      },
    }),
  ]);
  t.after(fetchMock.restore);

  await adminUsersClient.createInvitation(
    {
      email: "reviewer@example.com",
      roles: ["viewer", "reviewer"],
    },
    { csrfToken: "raw-csrf-token" },
  );
  await adminUsersClient.cancelInvitation(
    "22222222-2222-2222-2222-222222222222",
    { csrfToken: "raw-csrf-token" },
  );

  assert.equal(fetchMock.calls[0]?.init.method, "POST");
  assert.equal(fetchMock.calls[1]?.init.method, "POST");
  assert.equal(
    fetchMock.calls[1]?.input,
    "/api/docmind/auth/invitations/22222222-2222-2222-2222-222222222222/cancel",
  );
  assert.equal(
    new Headers(fetchMock.calls[0]?.init.headers).get("X-CSRF-Token"),
    "raw-csrf-token",
  );
  assert.equal(
    new Headers(fetchMock.calls[1]?.init.headers).get("X-CSRF-Token"),
    "raw-csrf-token",
  );
  assert.deepEqual(JSON.parse(String(fetchMock.calls[0]?.init.body)), {
    email: "reviewer@example.com",
    roles: ["viewer", "reviewer"],
  });
});

interface FetchCall {
  input: string;
  init: RequestInit;
}

function installFetchMock(responses: Response[]) {
  const originalFetch = globalThis.fetch;
  const calls: FetchCall[] = [];

  globalThis.fetch = (async (input, init = {}) => {
    calls.push({ input: input.toString(), init });
    const response = responses.shift();

    if (!response) {
      throw new Error("Unexpected fetch call.");
    }

    return response;
  }) as typeof fetch;

  return {
    calls,
    restore: () => {
      globalThis.fetch = originalFetch;
    },
  };
}

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    headers: {
      "content-type": "application/json",
      ...init.headers,
    },
    status: init.status ?? 200,
    statusText: init.statusText,
  });
}

function invitationResponseBody(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    accepted_at: null,
    accepted_by_user_id: null,
    cancelled_at: null,
    cancelled_by_user_id: null,
    created_at: "2026-06-11T12:00:00Z",
    created_by_user_id: "11111111-1111-1111-1111-111111111111",
    email: "invited.user@example.com",
    expires_at: "2026-06-18T12:00:00Z",
    id: "22222222-2222-2222-2222-222222222222",
    roles: ["viewer"],
    status: "pending",
    updated_at: "2026-06-11T12:00:00Z",
    ...overrides,
  };
}

function managedUserResponseBody(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    auth_providers: ["local"],
    created_at: "2026-06-24T10:00:00Z",
    display_name: "Managed User",
    email: "managed.user@example.com",
    id: "22222222-2222-2222-2222-222222222222",
    roles: ["viewer"],
    status: "active",
    updated_at: "2026-06-24T10:00:00Z",
    ...overrides,
  };
}
