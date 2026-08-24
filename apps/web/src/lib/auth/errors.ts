import { isApiError } from "@/lib/api/errors";

export type LoginFormErrorKey =
  | "accountDisabled"
  | "invalidCredentials"
  | "temporarilyLocked"
  | "untrustedOrigin"
  | "generic";

export interface LoginFormError {
  key: LoginFormErrorKey;
  values?: {
    minutes: number;
  };
}

export function isAuthenticationError(error: unknown): boolean {
  return isApiError(error) && error.status === 401;
}

export function isCsrfProtectionError(error: unknown): boolean {
  return (
    isApiError(error) &&
    (error.code === "CSRF_TOKEN_REQUIRED" ||
      error.code === "CSRF_TOKEN_REJECTED")
  );
}

export function getLoginFormError(error: unknown): LoginFormError {
  if (!isApiError(error)) {
    return { key: "generic" };
  }

  if (error.code === "INVALID_CREDENTIALS") {
    return { key: "invalidCredentials" };
  }

  if (error.code === "LOCAL_LOGIN_TEMPORARILY_LOCKED") {
    return {
      key: "temporarilyLocked",
      values: {
        minutes: retryAfterMinutes(error.details.retry_after_seconds),
      },
    };
  }

  if (error.code === "LOCAL_ACCOUNT_DISABLED") {
    return { key: "accountDisabled" };
  }

  if (error.code === "UNTRUSTED_BROWSER_ORIGIN") {
    return { key: "untrustedOrigin" };
  }

  return { key: "generic" };
}

export function getLoginFormErrorKey(error: unknown): LoginFormErrorKey {
  return getLoginFormError(error).key;
}

function retryAfterMinutes(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return 1;
  }

  return Math.max(1, Math.ceil(value / 60));
}
