import {
  buildDocmindProxyTargetUrl,
  createDocmindProxyAbortSignal,
  proxyDocmindUpstreamRequest,
} from "@/lib/api/proxy";
import type { ServerConfigErrorReason } from "@/lib/config/server-values";

export interface DocmindProxyRouteConfig {
  docmindApiInternalBaseUrl: string | null;
  docmindApiProxyUpstreamTimeoutMs: number;
  proxyConfigError: ServerConfigErrorReason | null;
}

export async function proxyDocmindApiRequest(
  request: Request,
  config: DocmindProxyRouteConfig,
): Promise<Response> {
  if (config.proxyConfigError !== null) {
    writeProxyError(config.proxyConfigError, request);
    return proxyErrorResponse(
      config.proxyConfigError === "missing_internal_api_base_url"
        ? "DOCMIND_API_PROXY_NOT_CONFIGURED"
        : "DOCMIND_API_PROXY_INVALID_CONFIG",
      503,
    );
  }

  const internalApiBaseUrl = config.docmindApiInternalBaseUrl;
  if (internalApiBaseUrl === null) {
    writeProxyError("missing_internal_api_base_url", request);
    return proxyErrorResponse("DOCMIND_API_PROXY_NOT_CONFIGURED", 503);
  }

  let targetUrl: URL;
  try {
    targetUrl = buildDocmindProxyTargetUrl(internalApiBaseUrl, request.url);
  } catch {
    writeProxyError("invalid_proxy_path", request);
    return proxyErrorResponse("DOCMIND_API_PROXY_INVALID_PATH", 400);
  }

  const upstreamAbortSignal = createDocmindProxyAbortSignal(
    request.signal,
    config.docmindApiProxyUpstreamTimeoutMs,
  );

  try {
    return await proxyDocmindUpstreamRequest(
      targetUrl,
      request,
      upstreamAbortSignal.signal,
    );
  } catch (error) {
    if (upstreamAbortSignal.timedOut()) {
      writeProxyError("upstream_fetch_timeout", request, error);
      return proxyErrorResponse("DOCMIND_API_PROXY_UPSTREAM_TIMEOUT", 504);
    }

    writeProxyError("upstream_fetch_failed", request, error);
    return proxyErrorResponse("DOCMIND_API_PROXY_UPSTREAM_UNAVAILABLE", 502);
  } finally {
    upstreamAbortSignal.dispose();
  }
}

function proxyErrorResponse(code: string, status: number): Response {
  return Response.json(
    {
      error: {
        code,
        details: {},
        message: "DocMind API proxy request failed.",
      },
    },
    { status },
  );
}

function writeProxyError(
  reason: string,
  request: Request,
  error?: unknown,
): void {
  const url = new URL(request.url);
  const errorName = error instanceof Error ? error.name : undefined;
  const message = `[docmind-web:api-proxy] reason=${reason} method=${request.method} path=${url.pathname}${errorName ? ` error=${errorName}` : ""}`;

  console.error(message);
}
