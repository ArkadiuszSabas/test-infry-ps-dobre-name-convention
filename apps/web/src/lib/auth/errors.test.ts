import assert from "node:assert/strict";
import test from "node:test";

import { ApiError } from "@/lib/api/errors";

import { getLoginFormError, getLoginFormErrorKey } from "./errors";

test("login form errors map invalid credentials to localized key", () => {
  const error = new ApiError({
    code: "INVALID_CREDENTIALS",
    message: "Raw API message.",
    status: 401,
  });

  assert.deepEqual(getLoginFormError(error), { key: "invalidCredentials" });
  assert.equal(getLoginFormErrorKey(error), "invalidCredentials");
});

test("login form errors map temporary lock with rounded retry minutes", () => {
  const error = new ApiError({
    code: "LOCAL_LOGIN_TEMPORARILY_LOCKED",
    details: {
      locked_until: "2026-05-20T09:05:00Z",
      retry_after_seconds: 121,
    },
    message: "Raw API message.",
    status: 429,
  });

  assert.deepEqual(getLoginFormError(error), {
    key: "temporarilyLocked",
    values: { minutes: 3 },
  });
});

test("login form errors map disabled local account to localized key", () => {
  const error = new ApiError({
    code: "LOCAL_ACCOUNT_DISABLED",
    message: "Raw API message.",
    status: 403,
  });

  assert.deepEqual(getLoginFormError(error), { key: "accountDisabled" });
});

test("login form errors fall back for unknown failures", () => {
  assert.deepEqual(getLoginFormError(new Error("network failed")), {
    key: "generic",
  });
});
