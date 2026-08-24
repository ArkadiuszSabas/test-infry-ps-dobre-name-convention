import * as http from "node:http";
import * as https from "node:https";
import { Readable } from "node:stream";

export const DOCMIND_API_PROXY_BASE_PATH = "/api/docmind";

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);
const BLOCKED_REQUEST_HEADERS = new Set([
  ...HOP_BY_HOP_HEADERS,
  "accept-encoding",
  "content-length",
  "host",
]);
const BLOCKED_RESPONSE_HEADERS = new Set([
  ...HOP_BY_HOP_HEADERS,
  "content-encoding",
  "content-length",
]);

export interface DocmindProxyAbortSignal {
  dispose: () => void;
  signal: AbortSignal;
  timedOut: () => boolean;
}

export function buildDocmindProxyTargetUrl(
  internalApiBaseUrl: string,
  requestUrl: string,
): URL {
  const incoming = new URL(requestUrl);
  const target = new URL(internalApiBaseUrl);
  const upstreamPath = upstreamPathname(incoming.pathname);

  target.pathname = upstreamPath;
  target.search = incoming.search;
  target.hash = "";

  return target;
}

export function proxyDocmindUpstreamRequest(
  targetUrl: URL,
  request: Request,
  signal: AbortSignal,
): Promise<Response> {
  const headers = proxyDocmindRequestHeaders(request.headers);
  const transport = targetUrl.protocol === "https:" ? https : http;

  return new Promise<Response>((resolve, reject) => {
    const upstreamRequest = transport.request(
      targetUrl,
      {
        headers,
        method: request.method,
      },
      (upstreamResponse) => {
        removeAbortListener();
        resolve(
          new Response(Readable.toWeb(upstreamResponse) as BodyInit, {
            headers: proxyResponseHeadersFromNode(upstreamResponse.headers),
            status: upstreamResponse.statusCode ?? 502,
            statusText: upstreamResponse.statusMessage ?? "",
          }),
        );
      },
    );

    const abortUpstreamRequest = (): void => {
      upstreamRequest.destroy(
        signal.reason instanceof Error
          ? signal.reason
          : new Error("DocMind API proxy request aborted."),
      );
    };
    const removeAbortListener = (): void => {
      signal.removeEventListener("abort", abortUpstreamRequest);
    };

    upstreamRequest.once("error", (error) => {
      removeAbortListener();
      reject(error);
    });
    if (signal.aborted) {
      abortUpstreamRequest();
      return;
    }
    signal.addEventListener("abort", abortUpstreamRequest, { once: true });

    if (request.body === null) {
      upstreamRequest.end();
      return;
    }

    Readable.fromWeb(
      request.body as import("node:stream/web").ReadableStream,
    ).pipe(upstreamRequest);
  });
}

export function createDocmindProxyAbortSignal(
  clientSignal: AbortSignal,
  timeoutMs: number,
): DocmindProxyAbortSignal {
  const controller = new AbortController();
  let timedOut = false;

  const abortFromClient = (): void => {
    controller.abort(clientSignal.reason);
  };

  if (clientSignal.aborted) {
    abortFromClient();
  } else {
    clientSignal.addEventListener("abort", abortFromClient, { once: true });
  }

  const timeout = setTimeout(() => {
    timedOut = true;
    controller.abort(
      new DOMException("DocMind API proxy upstream timeout.", "TimeoutError"),
    );
  }, timeoutMs);

  return {
    dispose: () => {
      clearTimeout(timeout);
      clientSignal.removeEventListener("abort", abortFromClient);
    },
    signal: controller.signal,
    timedOut: () => timedOut,
  };
}

export function proxyRequestHeaders(headers: Headers): Headers {
  const forwarded = new Headers();

  headers.forEach((value, key) => {
    if (!BLOCKED_REQUEST_HEADERS.has(key.toLowerCase())) {
      forwarded.append(key, value);
    }
  });

  return forwarded;
}

export function proxyResponseHeaders(headers: Headers): Headers {
  const forwarded = new Headers();

  headers.forEach((value, key) => {
    const normalizedKey = key.toLowerCase();
    if (
      normalizedKey !== "set-cookie" &&
      !BLOCKED_RESPONSE_HEADERS.has(normalizedKey)
    ) {
      forwarded.append(key, value);
    }
  });

  for (const cookie of setCookieHeaders(headers)) {
    forwarded.append("set-cookie", cookie);
  }

  return forwarded;
}

function proxyDocmindRequestHeaders(
  headers: Headers,
): http.OutgoingHttpHeaders {
  const forwarded = proxyRequestHeaders(headers);
  const result: http.OutgoingHttpHeaders = {};
  forwarded.forEach((value, key) => {
    result[key] = value;
  });
  return result;
}

function proxyResponseHeadersFromNode(
  headers: http.IncomingHttpHeaders,
): Headers {
  const responseHeaders = new Headers();
  for (const [key, value] of Object.entries(headers)) {
    if (value === undefined) {
      continue;
    }
    for (const item of Array.isArray(value) ? value : [value]) {
      responseHeaders.append(key, item);
    }
  }
  return proxyResponseHeaders(responseHeaders);
}

function upstreamPathname(pathname: string): string {
  if (pathname === DOCMIND_API_PROXY_BASE_PATH) {
    return "/";
  }

  const prefix = `${DOCMIND_API_PROXY_BASE_PATH}/`;
  if (!pathname.startsWith(prefix)) {
    throw new Error("Request URL is outside the DocMind API proxy path.");
  }

  return pathname.slice(DOCMIND_API_PROXY_BASE_PATH.length);
}

function setCookieHeaders(headers: Headers): string[] {
  const withSetCookie = headers as unknown as {
    getSetCookie?: () => string[];
  };
  const cookies = withSetCookie.getSetCookie?.() ?? [];

  if (cookies.length > 0) {
    return cookies;
  }

  const cookie = headers.get("set-cookie");
  return cookie ? [cookie] : [];
}
