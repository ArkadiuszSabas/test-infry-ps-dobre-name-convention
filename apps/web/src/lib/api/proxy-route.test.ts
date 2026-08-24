import assert from "node:assert/strict";
import test from "node:test";

import { proxyDocmindApiRequest } from "./proxy-route";

test("docmind proxy route maps upstream timeout to a sanitized 504 response", async () => {
  const originalFetch = globalThis.fetch;
  const originalConsoleError = console.error;

  console.error = () => {};
  globalThis.fetch = ((_input, init) =>
    new Promise<Response>((_resolve, reject) => {
      const signal = init?.signal;
      if (!(signal instanceof AbortSignal)) {
        reject(new Error("Expected a proxy abort signal."));
        return;
      }

      if (signal.aborted) {
        reject(signal.reason);
        return;
      }

      signal.addEventListener("abort", () => reject(signal.reason), {
        once: true,
      });
    })) as typeof fetch;

  try {
    const response = await proxyDocmindApiRequest(
      new Request("https://web.example.test/api/docmind/health/live"),
      {
        docmindApiInternalBaseUrl: "https://api.internal.example.test",
        docmindApiProxyUpstreamTimeoutMs: 1,
        proxyConfigError: null,
      },
    );

    assert.equal(response.status, 504);
    assert.deepEqual(await response.json(), {
      error: {
        code: "DOCMIND_API_PROXY_UPSTREAM_TIMEOUT",
        details: {},
        message: "DocMind API proxy request failed.",
      },
    });
  } finally {
    globalThis.fetch = originalFetch;
    console.error = originalConsoleError;
  }
});
