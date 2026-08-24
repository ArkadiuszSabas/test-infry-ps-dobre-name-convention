import "server-only";

import { request as httpRequest } from "node:http";
import { request as httpsRequest } from "node:https";

import type {
  DevLogLevel,
  NormalizedDevLogEvent,
} from "@/lib/observability/dev-log-event";

export interface SeqDeliveryResult {
  status: "sent" | "disabled" | "failed";
  reason?: string;
}

const SERVICE_NAME = "docmind-web";
const LOCAL_ENVIRONMENT = "local";
const DEFAULT_SEQ_URL = "http://localhost:5341";
const DEFAULT_SEQ_TIMEOUT_SECONDS = 0.5;
const DEFAULT_TERMINAL_LEVEL: DevLogLevel = "warn";
const LEVEL_ORDER: Record<DevLogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

const ANSI: Record<DevLogLevel | "reset" | "muted", string> = {
  debug: "\u001b[36m",
  info: "\u001b[34m",
  warn: "\u001b[33m",
  error: "\u001b[31m",
  muted: "\u001b[90m",
  reset: "\u001b[0m",
};

export function isLocalDevLoggingEnabled(): boolean {
  return (
    process.env.NODE_ENV === "development" &&
    envBoolean("DOCMIND_WEB_DEV_LOG_ENABLED", true)
  );
}

export async function sendDevLogToSeq(
  event: NormalizedDevLogEvent,
): Promise<SeqDeliveryResult> {
  const settings = seqSettings();
  if (!settings.enabled) {
    return { status: "disabled", reason: "disabled" };
  }

  const endpoint = seqIngestEndpoint(settings.url);
  if (endpoint === null) {
    return { status: "failed", reason: "invalid_seq_url" };
  }

  const headers: Record<string, string> = {
    "content-type": "application/vnd.serilog.clef",
  };

  if (settings.apiKey !== null) {
    headers["x-seq-apikey"] = settings.apiKey;
  }

  try {
    const response = await postSeqClef(
      endpoint,
      `${JSON.stringify(toSeqClefEvent(event))}\n`,
      headers,
      settings.timeoutMs,
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      return { status: "failed", reason: `http_${response.statusCode}` };
    }

    return { status: "sent" };
  } catch (error) {
    return {
      status: "failed",
      reason: error instanceof Error ? error.name : "request_failed",
    };
  }
}

export function writeDevLogToTerminal(
  event: NormalizedDevLogEvent,
  seqResult: SeqDeliveryResult,
): void {
  if (!shouldWriteTerminalLog(event)) {
    return;
  }

  const timestamp = new Date(event.timestamp).toLocaleTimeString("pl-PL", {
    hour12: false,
  });
  const levelLabel = event.level.toUpperCase().padEnd(5);
  const path = event.pathname === null ? "" : ` path=${event.pathname}`;
  const seq = ` seq=${seqResult.status}${seqResult.reason ? `:${seqResult.reason}` : ""}`;
  const details = terminalDetails(event);
  const line = `${timestamp} ${levelLabel} [${SERVICE_NAME}:${event.category}] ${event.message}${path}${seq}${details}`;
  const formattedLine = colorize(event.level, line);

  if (event.level === "error") {
    console.error(formattedLine);
    return;
  }

  if (event.level === "warn") {
    console.warn(formattedLine);
    return;
  }

  console.info(formattedLine);
}

function shouldWriteTerminalLog(event: NormalizedDevLogEvent): boolean {
  if (!envBoolean("DOCMIND_WEB_DEV_LOG_TERMINAL_ENABLED", true)) {
    return false;
  }

  if (event.category === "browser-console") {
    return false;
  }

  const threshold = terminalLevel();
  return LEVEL_ORDER[event.level] >= LEVEL_ORDER[threshold];
}

function terminalDetails(event: NormalizedDevLogEvent): string {
  const usefulKeys = [
    "metric_name",
    "value",
    "rating",
    "source",
    "line",
    "column",
  ];
  const details = usefulKeys
    .map((key) => {
      const value = event.details[key];
      return value === undefined || value === null ? null : `${key}=${value}`;
    })
    .filter((value): value is string => value !== null);

  if (details.length === 0) {
    return "";
  }

  return ` ${colorize("muted", details.join(" "))}`;
}

function toSeqClefEvent(event: NormalizedDevLogEvent): Record<string, unknown> {
  const clefEvent: Record<string, unknown> = {
    "@t": event.timestamp,
    "@mt": "{category}: {message}",
    "@l": toSeqLevel(event.level),
    service_name: SERVICE_NAME,
    environment: LOCAL_ENVIRONMENT,
    source: event.source,
    category: event.category,
    message: event.message,
    pathname: event.pathname,
    details: event.details,
  };

  const stack = event.details.stack;
  if (typeof stack === "string" && stack !== "") {
    clefEvent["@x"] = stack;
  }

  return clefEvent;
}

function toSeqLevel(level: DevLogLevel): string {
  if (level === "debug") {
    return "Debug";
  }

  if (level === "warn") {
    return "Warning";
  }

  if (level === "error") {
    return "Error";
  }

  return "Information";
}

function seqSettings(): {
  enabled: boolean;
  url: string;
  apiKey: string | null;
  timeoutMs: number;
} {
  const webSeqEnabled = envBooleanOrNull("DOCMIND_WEB_DEV_LOG_SEQ_ENABLED");
  const sharedSeqEnabled = envBoolean("DOCMIND_LOG_SEQ_ENABLED", true);

  return {
    enabled: webSeqEnabled ?? sharedSeqEnabled,
    url: process.env.DOCMIND_LOG_SEQ_URL ?? DEFAULT_SEQ_URL,
    apiKey: blankToNull(process.env.DOCMIND_LOG_SEQ_API_KEY),
    timeoutMs: secondsToMilliseconds(
      process.env.DOCMIND_LOG_SEQ_TIMEOUT_SECONDS,
      DEFAULT_SEQ_TIMEOUT_SECONDS,
    ),
  };
}

function seqIngestEndpoint(rawUrl: string): string | null {
  try {
    const url = new URL(rawUrl.includes("://") ? rawUrl : `http://${rawUrl}`);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return null;
    }

    const pathname = url.pathname.replaceAll(/\/+$/g, "");
    url.pathname = pathname.endsWith("/ingest/clef")
      ? pathname
      : `${pathname}/ingest/clef`;
    url.search = "";
    url.hash = "";

    return url.toString();
  } catch {
    return null;
  }
}

function postSeqClef(
  endpoint: string,
  body: string,
  headers: Record<string, string>,
  timeoutMs: number,
): Promise<{ statusCode: number }> {
  return new Promise((resolve, reject) => {
    const url = new URL(endpoint);
    const request = url.protocol === "https:" ? httpsRequest : httpRequest;
    const clientRequest = request(
      url,
      {
        method: "POST",
        headers: {
          ...headers,
          "content-length": String(Buffer.byteLength(body)),
        },
        timeout: timeoutMs,
      },
      (response) => {
        response.resume();
        response.on("end", () => {
          resolve({ statusCode: response.statusCode ?? 0 });
        });
      },
    );

    clientRequest.on("timeout", () => {
      clientRequest.destroy(new Error("TimeoutError"));
    });
    clientRequest.on("error", reject);
    clientRequest.end(body);
  });
}

function terminalLevel(): DevLogLevel {
  const rawLevel = process.env.DOCMIND_WEB_DEV_LOG_TERMINAL_LEVEL;
  if (
    rawLevel === "debug" ||
    rawLevel === "info" ||
    rawLevel === "warn" ||
    rawLevel === "error"
  ) {
    return rawLevel;
  }

  return DEFAULT_TERMINAL_LEVEL;
}

function envBoolean(name: string, defaultValue: boolean): boolean {
  return envBooleanOrNull(name) ?? defaultValue;
}

function envBooleanOrNull(name: string): boolean | null {
  const value = process.env[name]?.trim().toLowerCase();
  if (value === undefined || value === "") {
    return null;
  }

  if (["1", "true", "yes", "on"].includes(value)) {
    return true;
  }

  if (["0", "false", "no", "off"].includes(value)) {
    return false;
  }

  return null;
}

function blankToNull(value: string | undefined): string | null {
  if (value === undefined || value.trim() === "") {
    return null;
  }

  return value;
}

function secondsToMilliseconds(
  value: string | undefined,
  defaultValue: number,
): number {
  if (value === undefined || value.trim() === "") {
    return defaultValue * 1_000;
  }

  const seconds = Number.parseFloat(value);
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return defaultValue * 1_000;
  }

  return Math.min(seconds, 10) * 1_000;
}

function colorize(level: DevLogLevel | "muted", value: string): string {
  if (process.env.NO_COLOR !== undefined || process.env.TERM === "dumb") {
    return value;
  }

  return `${ANSI[level]}${value}${ANSI.reset}`;
}
