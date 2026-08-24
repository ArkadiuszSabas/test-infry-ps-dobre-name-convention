"use client";

import { useEffect } from "react";
import { useReportWebVitals } from "next/web-vitals";

import {
  errorDetails,
  reportBrowserDevLog,
  reportConsoleDevLog,
} from "@/lib/observability/dev-log-client";

const reportedWebVitalIds = new Set<string>();

export function DevObservability() {
  useReportWebVitals((metric) => {
    const metricKey = `${metric.name}:${metric.id}`;

    if (reportedWebVitalIds.has(metricKey)) {
      return;
    }

    reportedWebVitalIds.add(metricKey);

    const rating = metric.rating ?? "unknown";
    const level = rating === "good" || rating === "unknown" ? "info" : "warn";

    reportBrowserDevLog({
      level,
      category: "web-vital",
      message: `Web vital ${metric.name}: ${formatMetricValue(metric.value)} (${rating})`,
      details: {
        metric_name: metric.name,
        value: roundMetricValue(metric.value),
        rating,
        id: metric.id,
        navigation_type: metric.navigationType ?? null,
      },
    });
  });

  useEffect(() => {
    const originalWarn = console.warn;
    const originalError = console.error;

    console.warn = (...args: unknown[]) => {
      originalWarn(...args);
      reportConsoleDevLog("warn", args);
    };

    console.error = (...args: unknown[]) => {
      originalError(...args);
      reportConsoleDevLog("error", args);
    };

    const handleError = (event: ErrorEvent) => {
      reportBrowserDevLog({
        level: "error",
        category: "browser-error",
        message: `Unhandled browser error: ${event.message}`,
        details: {
          source: event.filename || null,
          line: event.lineno || null,
          column: event.colno || null,
          ...errorDetails(event.error),
        },
      });
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      reportBrowserDevLog({
        level: "error",
        category: "unhandled-rejection",
        message: "Unhandled promise rejection",
        details: errorDetails(event.reason),
      });
    };

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleUnhandledRejection);

    return () => {
      console.warn = originalWarn;
      console.error = originalError;
      window.removeEventListener("error", handleError);
      window.removeEventListener(
        "unhandledrejection",
        handleUnhandledRejection,
      );
    };
  }, []);

  return null;
}

function formatMetricValue(value: number): string {
  return value >= 100
    ? `${Math.round(value)} ms`
    : String(roundMetricValue(value));
}

function roundMetricValue(value: number): number {
  return Math.round(value * 100) / 100;
}
