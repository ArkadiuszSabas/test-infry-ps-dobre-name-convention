import {
  DEV_LOG_ENDPOINT,
  normalizeDevLogPayload,
  sanitizeLogMessage,
  type BrowserDevLogPayload,
  type DevLogDetails,
  type DevLogLevel,
} from "@/lib/observability/dev-log-event";

type BrowserDevLogInput = Omit<
  BrowserDevLogPayload,
  "source" | "timestamp" | "pathname"
> & {
  timestamp?: string;
  pathname?: string;
};

export function reportBrowserDevLog(input: BrowserDevLogInput): void {
  if (process.env.NODE_ENV !== "development" || typeof window === "undefined") {
    return;
  }

  const payload: BrowserDevLogPayload = {
    source: "browser",
    timestamp: input.timestamp ?? new Date().toISOString(),
    pathname: input.pathname ?? window.location.pathname,
    level: input.level,
    category: input.category,
    message: sanitizeLogMessage(input.message),
    details: withBrowserDetails(input.details),
  };
  const safePayload = normalizeDevLogPayload(payload);

  if (safePayload === null) {
    return;
  }

  void fetch(DEV_LOG_ENDPOINT, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(safePayload),
    keepalive: true,
  }).catch(() => {
    // Logging must never break the UI or create recursive console noise.
  });
}

export function reportConsoleDevLog(
  level: Extract<DevLogLevel, "warn" | "error">,
  args: readonly unknown[],
): void {
  reportBrowserDevLog({
    level,
    category: "browser-console",
    message: formatConsoleArgs(args),
    details: {
      argument_count: args.length,
      stack: firstApplicationStackFrame(new Error().stack),
    },
  });
}

export function errorDetails(error: unknown): DevLogDetails {
  if (error instanceof Error) {
    return {
      error_name: error.name,
      error_message: error.message,
      stack: error.stack ?? null,
    };
  }

  return {
    error_name: typeof error,
    error_message: formatConsoleValue(error),
  };
}

function withBrowserDetails(details: DevLogDetails | undefined): DevLogDetails {
  return {
    viewport: `${window.innerWidth}x${window.innerHeight}`,
    visibility_state: document.visibilityState,
    online: navigator.onLine,
    ...details,
  };
}

function formatConsoleArgs(args: readonly unknown[]): string {
  if (args.length === 0) {
    return "[empty console call]";
  }

  return sanitizeLogMessage(args.map(formatConsoleValue).join(" "));
}

function formatConsoleValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  if (
    typeof value === "number" ||
    typeof value === "boolean" ||
    value === null
  ) {
    return String(value);
  }

  if (value instanceof Error) {
    return `${value.name}: ${value.message}`;
  }

  if (Array.isArray(value)) {
    return `[array length=${value.length}]`;
  }

  if (typeof value === "object" && value !== null) {
    const keys = Object.keys(value).slice(0, 8);
    return `[object keys=${keys.join(",")}]`;
  }

  if (typeof value === "undefined") {
    return "[undefined]";
  }

  return String(value);
}

function firstApplicationStackFrame(stack: string | undefined): string | null {
  if (stack === undefined) {
    return null;
  }

  return (
    stack
      .split("\n")
      .map((line) => line.trim())
      .find(
        (line) =>
          line !== "" &&
          !line.includes("dev-log-client") &&
          !line.includes("dev-observability"),
      ) ?? null
  );
}
