import assert from "node:assert/strict";
import test from "node:test";

import { authClient } from "./api";

test("auth client unwraps the current actor envelope", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        auth_providers: ["local"],
        email: "actor@example.test",
        permissions: ["documents.read"],
        provider: "local",
        roles: ["reviewer"],
        user_id: "user-1",
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  const actor = await authClient.me();

  assert.deepEqual(actor, {
    auth_providers: ["local"],
    email: "actor@example.test",
    permissions: ["documents.read"],
    provider: "local",
    roles: ["reviewer"],
    user_id: "user-1",
  });
});

test("auth client login unwraps user/session/csrf without token storage", async (t) => {
  const storageMock = installStorageTrap();
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        csrf: {
          header_name: "X-CSRF-Token",
          token: "raw-csrf-token",
        },
        session: {
          expires_at: "2026-05-20T17:00:00Z",
        },
        user: {
          auth_providers: ["local"],
          email: "actor@example.test",
          permissions: ["documents.read"],
          provider: "local",
          roles: ["reviewer"],
          user_id: "user-1",
        },
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);
  t.after(storageMock.restore);

  const result = await authClient.loginLocal({
    login: "actor@example.test",
    password: "secret-password",
  });

  assert.equal(result.csrf.token, "raw-csrf-token");
  assert.equal(result.user.email, "actor@example.test");
  assert.equal(fetchMock.calls.length, 1);
  assert.equal(fetchMock.calls[0]?.init.credentials, "include");
  assert.equal(fetchMock.calls[0]?.init.method, "POST");
  assert.deepEqual(JSON.parse(String(fetchMock.calls[0]?.init.body)), {
    login: "actor@example.test",
    password: "secret-password",
  });
  assert.equal(storageMock.writeCount, 0);
});

test("auth client changes current user password with CSRF token", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse({
      data: { changed: true },
      meta: {
        evaluated_at: "2026-06-24T12:00:00Z",
        revoked_sessions: 2,
      },
    }),
  ]);
  t.after(fetchMock.restore);

  const result = await authClient.changeOwnPassword(
    {
      current_password: "old-secret",
      new_password: "new-secret",
    },
    { csrfToken: "raw-csrf-token" },
  );

  assert.deepEqual(result, { changed: true });
  assert.equal(fetchMock.calls[0]?.input, "/api/docmind/auth/me/password");
  assert.equal(fetchMock.calls[0]?.init.method, "PUT");
  assert.equal(
    new Headers(fetchMock.calls[0]?.init.headers).get("X-CSRF-Token"),
    "raw-csrf-token",
  );
  assert.deepEqual(JSON.parse(String(fetchMock.calls[0]?.init.body)), {
    current_password: "old-secret",
    new_password: "new-secret",
  });
});

test("auth client builds API-owned Entra start URLs", () => {
  const url = authClient.startEntraLogin("https://web.example.test/pl");
  const parsed = new URL(url, "https://web.example.test");

  assert.equal(parsed.origin, "https://web.example.test");
  assert.equal(url.startsWith("/api/docmind/"), true);
  assert.equal(parsed.pathname, "/api/docmind/auth/entra/start");
  assert.equal(
    parsed.searchParams.get("redirect_target"),
    "https://web.example.test/pl",
  );
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

function installStorageTrap() {
  const localStorageDescriptor = Object.getOwnPropertyDescriptor(
    globalThis,
    "localStorage",
  );
  const sessionStorageDescriptor = Object.getOwnPropertyDescriptor(
    globalThis,
    "sessionStorage",
  );
  let writeCount = 0;
  const storage = {
    setItem() {
      writeCount += 1;
    },
  };

  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: storage,
  });
  Object.defineProperty(globalThis, "sessionStorage", {
    configurable: true,
    value: storage,
  });

  return {
    get writeCount() {
      return writeCount;
    },
    restore: () => {
      restoreDescriptor("localStorage", localStorageDescriptor);
      restoreDescriptor("sessionStorage", sessionStorageDescriptor);
    },
  };
}

function restoreDescriptor(
  property: "localStorage" | "sessionStorage",
  descriptor: PropertyDescriptor | undefined,
) {
  if (descriptor) {
    Object.defineProperty(globalThis, property, descriptor);
  } else {
    delete (globalThis as Record<string, unknown>)[property];
  }
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
