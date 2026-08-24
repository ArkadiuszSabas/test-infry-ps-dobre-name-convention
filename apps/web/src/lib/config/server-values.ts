export const DOCMIND_API_INTERNAL_BASE_URL_ENV =
  "DOCMIND_API_INTERNAL_BASE_URL";
export const DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS_ENV =
  "DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS";
export const DEFAULT_DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS = 30_000;

export type ServerConfigErrorReason =
  | "invalid_internal_api_base_url"
  | "invalid_proxy_upstream_timeout_ms"
  | "missing_internal_api_base_url";

export interface NormalizedInternalApiBaseUrl {
  error: ServerConfigErrorReason | null;
  url: string | null;
}

export interface NormalizedProxyUpstreamTimeoutMs {
  error: ServerConfigErrorReason | null;
  timeoutMs: number;
}

export function normalizeInternalApiBaseUrl(
  value: string | undefined,
): NormalizedInternalApiBaseUrl {
  if (value === undefined || value.trim() === "") {
    return { error: "missing_internal_api_base_url", url: null };
  }

  let parsed: URL;
  try {
    parsed = new URL(value.trim());
  } catch {
    return { error: "invalid_internal_api_base_url", url: null };
  }

  if (
    (parsed.protocol !== "http:" && parsed.protocol !== "https:") ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    return { error: "invalid_internal_api_base_url", url: null };
  }

  return { error: null, url: parsed.origin };
}

export function normalizeProxyUpstreamTimeoutMs(
  value: string | undefined,
): NormalizedProxyUpstreamTimeoutMs {
  if (value === undefined || value.trim() === "") {
    return {
      error: null,
      timeoutMs: DEFAULT_DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS,
    };
  }

  const timeoutMs = Number(value.trim());
  if (!Number.isSafeInteger(timeoutMs) || timeoutMs <= 0) {
    return {
      error: "invalid_proxy_upstream_timeout_ms",
      timeoutMs: DEFAULT_DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS,
    };
  }

  return { error: null, timeoutMs };
}
