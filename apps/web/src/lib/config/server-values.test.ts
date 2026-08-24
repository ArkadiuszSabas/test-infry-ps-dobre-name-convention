import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS,
  normalizeInternalApiBaseUrl,
  normalizeProxyUpstreamTimeoutMs,
} from "./server-values";

test("server config accepts an internal API origin", () => {
  assert.deepEqual(
    normalizeInternalApiBaseUrl("https://api.internal.example.test/"),
    {
      error: null,
      url: "https://api.internal.example.test",
    },
  );
});

test("server config defaults proxy upstream timeout", () => {
  assert.deepEqual(normalizeProxyUpstreamTimeoutMs(undefined), {
    error: null,
    timeoutMs: DEFAULT_DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS,
  });
});

test("server config accepts positive integer proxy upstream timeout", () => {
  assert.deepEqual(normalizeProxyUpstreamTimeoutMs("2500"), {
    error: null,
    timeoutMs: 2500,
  });
});

test("server config reports invalid proxy upstream timeouts", () => {
  assert.deepEqual(normalizeProxyUpstreamTimeoutMs("0"), {
    error: "invalid_proxy_upstream_timeout_ms",
    timeoutMs: DEFAULT_DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS,
  });
  assert.deepEqual(normalizeProxyUpstreamTimeoutMs("10.5"), {
    error: "invalid_proxy_upstream_timeout_ms",
    timeoutMs: DEFAULT_DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS,
  });
  assert.deepEqual(normalizeProxyUpstreamTimeoutMs("not a number"), {
    error: "invalid_proxy_upstream_timeout_ms",
    timeoutMs: DEFAULT_DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS,
  });
});

test("server config reports missing internal API origins", () => {
  assert.deepEqual(normalizeInternalApiBaseUrl(" "), {
    error: "missing_internal_api_base_url",
    url: null,
  });
});

test("server config reports malformed internal API origins without throwing", () => {
  assert.deepEqual(normalizeInternalApiBaseUrl("not a url"), {
    error: "invalid_internal_api_base_url",
    url: null,
  });
  assert.deepEqual(
    normalizeInternalApiBaseUrl("https://api.internal.example.test/private"),
    {
      error: "invalid_internal_api_base_url",
      url: null,
    },
  );
  assert.deepEqual(
    normalizeInternalApiBaseUrl("ftp://api.internal.example.test"),
    {
      error: "invalid_internal_api_base_url",
      url: null,
    },
  );
});
