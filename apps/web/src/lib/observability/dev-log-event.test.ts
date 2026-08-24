import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeDevLogPayload,
  sanitizeLogDetail,
  sanitizeLogMessage,
} from "@/lib/observability/dev-log-event";

test("sanitizeLogMessage redacts obvious sensitive fragments", () => {
  assert.equal(
    sanitizeLogMessage(
      "request failed token=abc authorization: Bearer abc password='secret'",
    ),
    "request failed token=[redacted] authorization: [redacted] password=[redacted]",
  );
});

test("sanitizeLogMessage strips URL query strings and fragments", () => {
  assert.equal(
    sanitizeLogMessage(
      "failed at /review?documentId=123&name=Jan#section and https://example.test/path?token=abc#secret and /path#secret and /#section?name=Jan and #standalone?name=Jan",
    ),
    "failed at /review?[redacted]#[redacted] and https://example.test/path?[redacted]#[redacted] and /path#[redacted] and /?[redacted]#[redacted] and #[redacted]",
  );
});

test("normalizeDevLogPayload sanitizes detail strings before transport", () => {
  const event = normalizeDevLogPayload({
    source: "browser",
    level: "error",
    category: "browser-error",
    message: "failed",
    details: {
      stack: "Error at /review?documentId=123&name=Jan#trace",
      source: "https://example.test/app?token=abc",
      error_message: "authorization: Bearer abc",
    },
  });

  assert.equal(event?.details.stack, "Error at /review?[redacted]#[redacted]");
  assert.equal(event?.details.source, "https://example.test/app?[redacted]");
  assert.equal(event?.details.error_message, "authorization: [redacted]");
});

test("sanitizeLogDetail redacts sensitive keys", () => {
  assert.equal(
    sanitizeLogDetail("connection_string", "UseDevelopmentStorage"),
    "[redacted]",
  );
  assert.equal(sanitizeLogDetail("safe_field", "value"), "value");
});

test("normalizeDevLogPayload accepts and sanitizes browser events", () => {
  const event = normalizeDevLogPayload(
    {
      source: "browser",
      level: "error",
      category: "browser-error",
      message: "failed token=abc",
      timestamp: "2026-05-14T10:15:30.000Z",
      pathname: "/dashboard",
      details: {
        password: "secret",
        line: 12,
      },
    },
    new Date("2026-05-14T11:00:00.000Z"),
  );

  assert.deepEqual(event, {
    source: "browser",
    level: "error",
    category: "browser-error",
    message: "failed token=[redacted]",
    timestamp: "2026-05-14T10:15:30.000Z",
    pathname: "/dashboard",
    details: {
      password: "[redacted]",
      line: 12,
    },
  });
});

test("normalizeDevLogPayload rejects malformed events", () => {
  assert.equal(normalizeDevLogPayload(null), null);
  assert.equal(
    normalizeDevLogPayload({
      source: "browser",
      level: "fatal",
      category: "browser-error",
      message: "failed",
    }),
    null,
  );
});
