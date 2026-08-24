import assert from "node:assert/strict";
import test from "node:test";

import { createServer } from "node:http";
import { once } from "node:events";

import {
  buildDocmindProxyTargetUrl,
  createDocmindProxyAbortSignal,
  proxyDocmindUpstreamRequest,
  proxyRequestHeaders,
  proxyResponseHeaders,
} from "./proxy";

test("docmind proxy builds upstream URLs from the same-origin proxy path", () => {
  const target = buildDocmindProxyTargetUrl(
    "https://api.internal.example.test",
    "https://web.example.test/api/docmind/documents?source=manual_upload&limit=50",
  );

  assert.equal(
    target.toString(),
    "https://api.internal.example.test/documents?source=manual_upload&limit=50",
  );
});

test("docmind proxy preserves relevant request headers and strips hop-by-hop headers", () => {
  const headers = proxyRequestHeaders(
    new Headers({
      connection: "keep-alive",
      "content-length": "123",
      "content-type": "application/json",
      cookie: "docmind_session=session-id",
      host: "web.example.test",
      "x-correlation-id": "correlation-1",
      "x-csrf-token": "csrf-token",
    }),
  );

  assert.equal(headers.get("content-type"), "application/json");
  assert.equal(headers.get("cookie"), "docmind_session=session-id");
  assert.equal(headers.get("x-correlation-id"), "correlation-1");
  assert.equal(headers.get("x-csrf-token"), "csrf-token");
  assert.equal(headers.get("connection"), null);
  assert.equal(headers.get("content-length"), null);
  assert.equal(headers.get("host"), null);
});

test("docmind proxy forwards body-bearing request responses", async () => {
  const server = createServer((incoming, outgoing) => {
    incoming.resume();
    incoming.once("end", () => {
      outgoing.writeHead(401, { "content-type": "application/json" });
      outgoing.end('{"error":"invalid key"}');
    });
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address();
  assert.ok(address !== null && typeof address !== "string");

  const formData = new FormData();
  formData.set("document_type_id", "supplier_invoice");
  formData.set(
    "file",
    new File([new Blob(["%PDF-1.7 pdf-bytes"])], "invoice.pdf", {
      type: "application/pdf",
    }),
  );
  try {
    const request = new Request(
      "https://web.example.test/api/docmind/documents/manual-upload",
      {
        body: formData,
        headers: {
          "x-csrf-token": "csrf-token",
        },
        method: "POST",
      },
    );
    const response = await proxyDocmindUpstreamRequest(
      new URL(`http://127.0.0.1:${address.port}`),
      request,
      new AbortController().signal,
    );

    assert.equal(response.status, 401);
    assert.equal(await response.text(), '{"error":"invalid key"}');
  } finally {
    server.close();
    await once(server, "close");
  }
});

test("docmind proxy abort signal times out upstream requests", async () => {
  const clientController = new AbortController();
  const proxySignal = createDocmindProxyAbortSignal(clientController.signal, 1);

  try {
    await new Promise<void>((resolve) => {
      proxySignal.signal.addEventListener("abort", () => resolve(), {
        once: true,
      });
    });

    assert.equal(proxySignal.timedOut(), true);
    assert.equal(proxySignal.signal.reason?.name, "TimeoutError");
  } finally {
    proxySignal.dispose();
  }
});

test("docmind proxy abort signal preserves client aborts separately from timeouts", () => {
  const clientController = new AbortController();
  const proxySignal = createDocmindProxyAbortSignal(
    clientController.signal,
    1_000,
  );

  try {
    clientController.abort(new DOMException("Client aborted.", "AbortError"));

    assert.equal(proxySignal.signal.aborted, true);
    assert.equal(proxySignal.timedOut(), false);
    assert.equal(proxySignal.signal.reason?.name, "AbortError");
  } finally {
    proxySignal.dispose();
  }
});

test("docmind proxy forwards upstream response status headers and cookies", () => {
  const upstreamHeaders = new Headers({
    connection: "close",
    "content-length": "128",
    "content-type": "application/json",
    "set-cookie": "docmind_session=session-id; HttpOnly; Path=/",
    "x-correlation-id": "correlation-1",
  });

  const headers = proxyResponseHeaders(upstreamHeaders);

  assert.equal(headers.get("content-type"), "application/json");
  assert.equal(headers.get("x-correlation-id"), "correlation-1");
  assert.equal(
    headers.get("set-cookie"),
    "docmind_session=session-id; HttpOnly; Path=/",
  );
  assert.equal(headers.get("connection"), null);
  assert.equal(headers.get("content-length"), null);
});

test("docmind proxy rejects URLs outside the proxy base path", () => {
  assert.throws(
    () =>
      buildDocmindProxyTargetUrl(
        "https://api.internal.example.test",
        "https://web.example.test/api/other/auth/me",
      ),
    /outside the DocMind API proxy path/,
  );
});
