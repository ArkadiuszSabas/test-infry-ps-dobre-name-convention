export const DEV_LOG_ENDPOINT = "/api/dev/logs";

export type DevLogLevel = "debug" | "info" | "warn" | "error";
export type DevLogCategory =
  | "browser-console"
  | "browser-error"
  | "unhandled-rejection"
  | "web-vital"
  | "manual";

export type DevLogDetail = string | number | boolean | null;
export type DevLogDetails = Record<string, DevLogDetail>;

export interface BrowserDevLogPayload {
  source: "browser";
  level: DevLogLevel;
  category: DevLogCategory;
  message: string;
  timestamp?: string;
  pathname?: string;
  details?: DevLogDetails;
}

export interface NormalizedDevLogEvent {
  source: "browser";
  level: DevLogLevel;
  category: DevLogCategory;
  message: string;
  timestamp: string;
  pathname: string | null;
  details: DevLogDetails;
}

const REDACTED = "[redacted]";
const MAX_MESSAGE_LENGTH = 1_000;
const MAX_DETAIL_LENGTH = 2_000;
const MAX_DETAIL_COUNT = 25;
const MAX_KEY_LENGTH = 80;

const LOG_LEVELS = new Set<DevLogLevel>(["debug", "info", "warn", "error"]);
const LOG_CATEGORIES = new Set<DevLogCategory>([
  "browser-console",
  "browser-error",
  "unhandled-rejection",
  "web-vital",
  "manual",
]);

const SENSITIVE_KEY_PARTS = [
  "authorization",
  "api_key",
  "apikey",
  "connection_string",
  "connectionstring",
  "cookie",
  "credential",
  "password",
  "secret",
  "token",
] as const;

const SENSITIVE_MESSAGE_PATTERNS = [
  /(\b(?:[a-z0-9_-]*(?:api[-_ ]?key|apikey|connection[-_ ]?string|connectionstring|cookie|credential|password|secret|token)[a-z0-9_-]*)\b\s*[:=]\s*)("[^"]*"|'[^']*'|[^\s,}\]]+)/gi,
  /(\bauthorization\b\s*[:=]\s*)("(?:Bearer|Basic)\s+[^"]*"|'(?:Bearer|Basic)\s+[^']*'|(?:Bearer|Basic)\s+[^\s,}\]]+|"[^"]*"|'[^']*'|[^\s,}\]]+)/gi,
];

export function normalizeDevLogPayload(
  payload: unknown,
  now: Date = new Date(),
): NormalizedDevLogEvent | null {
  if (!isRecord(payload)) {
    return null;
  }

  if (payload.source !== "browser") {
    return null;
  }

  if (!isDevLogLevel(payload.level) || !isDevLogCategory(payload.category)) {
    return null;
  }

  if (typeof payload.message !== "string" || payload.message.trim() === "") {
    return null;
  }

  return {
    source: "browser",
    level: payload.level,
    category: payload.category,
    message: truncate(
      sanitizeLogMessage(payload.message.trim()),
      MAX_MESSAGE_LENGTH,
    ),
    timestamp: normalizeTimestamp(payload.timestamp, now),
    pathname: normalizePathname(payload.pathname),
    details: normalizeDetails(payload.details),
  };
}

export function sanitizeLogMessage(message: string): string {
  const withoutUrlSensitiveParts = redactUrlSensitiveParts(message);

  return SENSITIVE_MESSAGE_PATTERNS.reduce(
    (safeMessage, pattern) => safeMessage.replace(pattern, `$1${REDACTED}`),
    withoutUrlSensitiveParts,
  );
}

export function sanitizeLogDetail(key: string, value: unknown): DevLogDetail {
  if (isSensitiveKey(key)) {
    return REDACTED;
  }

  if (typeof value === "string") {
    return truncate(sanitizeLogMessage(value), MAX_DETAIL_LENGTH);
  }

  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "boolean" || value === null) {
    return value;
  }

  return summarizeUnknownValue(value);
}

function normalizeDetails(value: unknown): DevLogDetails {
  if (!isRecord(value)) {
    return {};
  }

  const normalizedDetails: DevLogDetails = {};
  const entries = Object.entries(value).slice(0, MAX_DETAIL_COUNT);

  for (const [rawKey, rawValue] of entries) {
    const key = normalizeDetailKey(rawKey);
    if (key === "") {
      continue;
    }

    normalizedDetails[key] = sanitizeLogDetail(key, rawValue);
  }

  return normalizedDetails;
}

function normalizeTimestamp(value: unknown, now: Date): string {
  if (typeof value !== "string") {
    return now.toISOString();
  }

  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return now.toISOString();
  }

  return new Date(timestamp).toISOString();
}

function normalizePathname(value: unknown): string | null {
  if (typeof value !== "string" || value.trim() === "") {
    return null;
  }

  return truncate(sanitizeLogMessage(value.trim()), 200);
}

function normalizeDetailKey(key: string): string {
  return truncate(
    key.trim().replaceAll(/[^a-zA-Z0-9_.-]/g, "_"),
    MAX_KEY_LENGTH,
  );
}

function isDevLogLevel(value: unknown): value is DevLogLevel {
  return typeof value === "string" && LOG_LEVELS.has(value as DevLogLevel);
}

function isDevLogCategory(value: unknown): value is DevLogCategory {
  return (
    typeof value === "string" && LOG_CATEGORIES.has(value as DevLogCategory)
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isSensitiveKey(key: string): boolean {
  const normalizedKey = key.toLowerCase().replaceAll(/[-\s]/g, "_");
  return SENSITIVE_KEY_PARTS.some((part) => normalizedKey.includes(part));
}

function summarizeUnknownValue(value: unknown): string {
  if (value instanceof Error) {
    return truncate(
      sanitizeLogMessage(`${value.name}: ${value.message}`),
      MAX_DETAIL_LENGTH,
    );
  }

  if (Array.isArray(value)) {
    return `[array length=${value.length}]`;
  }

  if (typeof value === "object" && value !== null) {
    return `[object ${Object.keys(value).slice(0, 8).join(",")}]`;
  }

  if (typeof value === "undefined") {
    return "[undefined]";
  }

  return truncate(sanitizeLogMessage(String(value)), MAX_DETAIL_LENGTH);
}

function truncate(value: string, maxLength: number): string {
  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, maxLength - 3)}...`;
}

function redactUrlSensitiveParts(message: string): string {
  return message
    .replace(
      /((?:https?:\/\/[^\s"'<>?#]+|\/[^\s"'<>?#]*))(?:\?[^\s"'<>#]*)?(#[^\s"'<>]*)/gi,
      (match: string, path: string) =>
        `${path}${match.includes("?") ? `?${REDACTED}` : ""}#[redacted]`,
    )
    .replace(
      /((?:https?:\/\/[^\s"'<>?#]+|\/[^\s"'<>?#]*))\?[^\s"'<>#]*/gi,
      (_match: string, path: string) => `${path}?${REDACTED}`,
    )
    .replace(
      /(^|[\s"'([])#[^\s"'<>]+/g,
      (_match: string, prefix: string) => `${prefix}#[redacted]`,
    );
}
