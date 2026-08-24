import assert from "node:assert/strict";
import test from "node:test";

import { createApiTransport, subscribeToAuthRefresh } from "./client";
import { ApiError } from "./errors";

test("api transport sends credentialed requests and parses JSON", async () => {
  const controller = new AbortController();
  const fetchMock = createFetchMock([
    jsonResponse({ data: { ok: true }, meta: {} }),
  ]);
  const transport = createApiTransport({
    baseUrl: "https://api.example.test",
    fetchFn: fetchMock.fetch,
  });

  const result = await transport.fetchJson("/auth/me", {
    signal: controller.signal,
  });

  assert.deepEqual(result, { data: { ok: true }, meta: {} });
  assert.equal(fetchMock.calls.length, 1);
  assert.equal(fetchMock.calls[0]?.url, "https://api.example.test/auth/me");
  assert.equal(fetchMock.calls[0]?.init.credentials, "include");
  assert.equal(fetchMock.calls[0]?.init.signal, controller.signal);
});

test("api transport supports same-origin proxy paths", async () => {
  const fetchMock = createFetchMock([
    jsonResponse({ data: { ok: true }, meta: {} }),
  ]);
  const transport = createApiTransport({
    baseUrl: "/api/docmind",
    fetchFn: fetchMock.fetch,
  });

  await transport.fetchJson("/documents?source=manual_upload");

  assert.equal(
    fetchMock.calls[0]?.url,
    "/api/docmind/documents?source=manual_upload",
  );
  assert.equal(fetchMock.calls[0]?.init.credentials, "include");
});

test("api transport defaults to the same-origin DocMind proxy", async () => {
  const fetchMock = createFetchMock([
    jsonResponse({ data: { ok: true }, meta: {} }),
  ]);
  const transport = createApiTransport({
    fetchFn: fetchMock.fetch,
  });

  await transport.fetchJson("/auth/me");

  assert.equal(fetchMock.calls[0]?.url, "/api/docmind/auth/me");
});

test("api transport keeps absolute local browser and API hosts aligned", async (t) => {
  const windowDescriptor = Object.getOwnPropertyDescriptor(
    globalThis,
    "window",
  );
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      location: {
        hostname: "localhost",
      },
    },
  });
  t.after(() => {
    if (windowDescriptor) {
      Object.defineProperty(globalThis, "window", windowDescriptor);
      return;
    }

    Reflect.deleteProperty(globalThis, "window");
  });

  const fetchMock = createFetchMock([
    jsonResponse({ data: { ok: true }, meta: {} }),
  ]);
  const transport = createApiTransport({
    baseUrl: "http://127.0.0.1:5001",
    fetchFn: fetchMock.fetch,
  });

  await transport.fetchJson("/auth/me");

  assert.equal(fetchMock.calls[0]?.url, "http://localhost:5001/auth/me");
});

test("api transport throws typed API errors from backend envelopes", async () => {
  const fetchMock = createFetchMock([
    jsonResponse(
      {
        error: {
          code: "AUTHENTICATION_REQUIRED",
          details: { reason: "missing_session" },
          message: "Authentication is required.",
        },
      },
      { status: 401 },
    ),
  ]);
  const transport = createApiTransport({
    baseUrl: "https://api.example.test",
    fetchFn: fetchMock.fetch,
  });

  await assert.rejects(
    () => transport.fetchJson("/auth/me", { retryAuth: false }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.status, 401);
      assert.equal(error.code, "AUTHENTICATION_REQUIRED");
      assert.equal(error.message, "Authentication is required.");
      assert.deepEqual(error.details, { reason: "missing_session" });
      return true;
    },
  );
});

test("api transport refreshes once and retries safe 401 responses", async () => {
  const fetchMock = createFetchMock([
    jsonResponse(
      {
        error: {
          code: "AUTHENTICATION_REQUIRED",
          details: {},
          message: "Authentication is required.",
        },
      },
      { status: 401 },
    ),
    jsonResponse({ data: { user: "refreshed" }, meta: {} }),
    jsonResponse({ data: { email: "user@example.test" }, meta: {} }),
  ]);
  const transport = createApiTransport({
    baseUrl: "https://api.example.test",
    fetchFn: fetchMock.fetch,
  });

  const result = await transport.fetchJson("/auth/me");

  assert.deepEqual(result, { data: { email: "user@example.test" }, meta: {} });
  assert.deepEqual(
    fetchMock.calls.map((call) => `${call.init.method} ${call.url}`),
    [
      "GET https://api.example.test/auth/me",
      "POST https://api.example.test/auth/refresh",
      "GET https://api.example.test/auth/me",
    ],
  );
});

test("api transport notifies auth refresh listeners after successful refresh", async (t) => {
  let refreshNotifications = 0;
  const unsubscribe = subscribeToAuthRefresh(() => {
    refreshNotifications += 1;
  });
  t.after(unsubscribe);

  const fetchMock = createFetchMock([
    jsonResponse(
      {
        error: {
          code: "AUTHENTICATION_REQUIRED",
          details: {},
          message: "Authentication is required.",
        },
      },
      { status: 401 },
    ),
    jsonResponse({ data: { user: "refreshed" }, meta: {} }),
    jsonResponse({ data: { email: "user@example.test" }, meta: {} }),
  ]);
  const transport = createApiTransport({
    baseUrl: "https://api.example.test",
    fetchFn: fetchMock.fetch,
  });

  await transport.fetchJson("/auth/me");

  assert.equal(refreshNotifications, 1);
});

test("api transport stops after an unsuccessful refresh attempt", async () => {
  const fetchMock = createFetchMock([
    jsonResponse(
      {
        error: {
          code: "AUTHENTICATION_REQUIRED",
          details: {},
          message: "Authentication is required.",
        },
      },
      { status: 401 },
    ),
    jsonResponse(
      {
        error: {
          code: "INVALID_REFRESH_TOKEN",
          details: {},
          message: "Authentication is required.",
        },
      },
      { status: 401 },
    ),
  ]);
  const transport = createApiTransport({
    baseUrl: "https://api.example.test",
    fetchFn: fetchMock.fetch,
  });

  await assert.rejects(() => transport.fetchJson("/auth/me"));

  assert.deepEqual(
    fetchMock.calls.map((call) => `${call.init.method} ${call.url}`),
    [
      "GET https://api.example.test/auth/me",
      "POST https://api.example.test/auth/refresh",
    ],
  );
});

test("api transport does not blindly retry unsafe 401 responses", async () => {
  const fetchMock = createFetchMock([
    jsonResponse(
      {
        error: {
          code: "AUTHENTICATION_REQUIRED",
          details: {},
          message: "Authentication is required.",
        },
      },
      { status: 401 },
    ),
  ]);
  const transport = createApiTransport({
    baseUrl: "https://api.example.test",
    fetchFn: fetchMock.fetch,
  });

  await assert.rejects(() =>
    transport.fetchJson("/documents", { json: { name: "A" }, method: "POST" }),
  );

  assert.deepEqual(
    fetchMock.calls.map((call) => `${call.init.method} ${call.url}`),
    ["POST https://api.example.test/documents"],
  );
});

test("api transport sends CSRF header only for unsafe requests", async () => {
  const fetchMock = createFetchMock([
    jsonResponse({ data: { created: true }, meta: {} }),
    jsonResponse({ data: { ok: true }, meta: {} }),
  ]);
  const transport = createApiTransport({
    baseUrl: "https://api.example.test",
    fetchFn: fetchMock.fetch,
  });

  await transport.fetchJson("/auth/logout", {
    csrfToken: "raw-csrf-token",
    method: "POST",
  });
  await transport.fetchJson("/auth/me", {
    csrfToken: "raw-csrf-token",
    method: "GET",
  });

  assert.equal(
    new Headers(fetchMock.calls[0]?.init.headers).get("X-CSRF-Token"),
    "raw-csrf-token",
  );
  assert.equal(
    new Headers(fetchMock.calls[1]?.init.headers).get("X-CSRF-Token"),
    null,
  );
});

interface FetchCall {
  url: string;
  init: RequestInit;
}

function createFetchMock(responses: Response[]) {
  const calls: FetchCall[] = [];
  const fetchMock: typeof fetch = async (input, init = {}) => {
    calls.push({
      url: input.toString(),
      init,
    });
    const response = responses.shift();

    if (!response) {
      throw new Error("Unexpected fetch call.");
    }

    return response;
  };

  return { calls, fetch: fetchMock };
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
