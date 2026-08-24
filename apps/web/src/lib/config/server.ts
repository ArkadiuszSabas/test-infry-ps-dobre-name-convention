import "server-only";

import {
  DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS_ENV,
  DOCMIND_API_INTERNAL_BASE_URL_ENV,
  normalizeInternalApiBaseUrl,
  normalizeProxyUpstreamTimeoutMs,
  type ServerConfigErrorReason,
} from "./server-values";

export interface ServerConfig {
  docmindApiInternalBaseUrl: string | null;
  docmindApiProxyUpstreamTimeoutMs: number;
  proxyConfigError: ServerConfigErrorReason | null;
}

export function getServerConfig(): ServerConfig {
  const internalApiBaseUrl = normalizeInternalApiBaseUrl(
    process.env[DOCMIND_API_INTERNAL_BASE_URL_ENV],
  );
  const proxyUpstreamTimeoutMs = normalizeProxyUpstreamTimeoutMs(
    process.env[DOCMIND_API_PROXY_UPSTREAM_TIMEOUT_MS_ENV],
  );

  return {
    docmindApiInternalBaseUrl: internalApiBaseUrl.url,
    docmindApiProxyUpstreamTimeoutMs: proxyUpstreamTimeoutMs.timeoutMs,
    proxyConfigError: internalApiBaseUrl.error ?? proxyUpstreamTimeoutMs.error,
  };
}
