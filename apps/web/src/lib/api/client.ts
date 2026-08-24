import { getPublicConfig } from "@/lib/config/public";

import { ApiError, apiErrorFromResponseBody } from "./errors";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const CSRF_HEADER_NAME = "X-CSRF-Token";
type AuthRefreshListener = () => void;

const authRefreshListeners = new Set<AuthRefreshListener>();

export interface ApiRequestOptions {
  method?: string;
  headers?: HeadersInit;
  body?: BodyInit | null;
  json?: unknown;
  signal?: AbortSignal;
  csrfToken?: string | null;
  retryAuth?: boolean;
}

export interface ApiBinaryRequestOptions extends ApiRequestOptions {
  expectedContentType: string;
}

export interface ApiTransportOptions {
  baseUrl?: string;
  fetchFn?: typeof fetch;
}

export interface ApiTransport {
  buildUrl: (path: string) => string;
  fetchBinary: (
    path: string,
    options: ApiBinaryRequestOptions,
  ) => Promise<Blob>;
  fetchJson: <TResponse>(
    path: string,
    options?: ApiRequestOptions,
  ) => Promise<TResponse>;
}

export function subscribeToAuthRefresh(listener: AuthRefreshListener) {
  authRefreshListeners.add(listener);

  return () => {
    authRefreshListeners.delete(listener);
  };
}

export function createApiTransport({
  baseUrl = getPublicConfig().docmindApiBaseUrl,
  fetchFn = (...args) => fetch(...args),
}: ApiTransportOptions = {}): ApiTransport {
  const normalizedBaseUrl = normalizeBaseUrl(
    resolveBrowserLocalApiBaseUrl(baseUrl),
  );

  function buildUrl(path: string): string {
    return joinApiBaseUrl(normalizedBaseUrl, path);
  }

  async function fetchJson<TResponse>(
    path: string,
    options: ApiRequestOptions = {},
  ): Promise<TResponse> {
    return sendJson<TResponse>(path, options, true);
  }

  async function fetchBinary(
    path: string,
    options: ApiBinaryRequestOptions,
  ): Promise<Blob> {
    return sendBinary(path, options, true);
  }

  async function sendJson<TResponse>(
    path: string,
    options: ApiRequestOptions,
    canRefresh: boolean,
  ): Promise<TResponse> {
    const method = normalizeMethod(options.method);
    const response = await fetchFn(buildUrl(path), {
      body: requestBody(options),
      credentials: "include",
      headers: requestHeaders(options, method),
      method,
      signal: options.signal,
    });

    if (
      response.status === 401 &&
      canRefresh &&
      options.retryAuth !== false &&
      SAFE_METHODS.has(method)
    ) {
      const refreshed = await refreshSession(options);

      if (refreshed) {
        return sendJson(path, { ...options, retryAuth: false }, false);
      }
    }

    if (!response.ok) {
      throw apiErrorFromResponseBody(response, await readJson(response));
    }

    if (response.status === 204) {
      return undefined as TResponse;
    }

    return (await readJson(response)) as TResponse;
  }

  async function sendBinary(
    path: string,
    options: ApiBinaryRequestOptions,
    canRefresh: boolean,
  ): Promise<Blob> {
    const method = normalizeMethod(options.method);
    const response = await fetchFn(buildUrl(path), {
      body: requestBody(options),
      credentials: "include",
      headers: requestHeaders(options, method),
      method,
      signal: options.signal,
    });

    if (
      response.status === 401 &&
      canRefresh &&
      options.retryAuth !== false &&
      SAFE_METHODS.has(method)
    ) {
      const refreshed = await refreshSession(options);

      if (refreshed) {
        return sendBinary(path, { ...options, retryAuth: false }, false);
      }
    }

    if (!response.ok) {
      throw apiErrorFromResponseBody(response, await readJson(response));
    }

    if (
      responseMediaType(response) !== options.expectedContentType.toLowerCase()
    ) {
      throw new ApiError({
        status: response.status,
        code: "INVALID_API_RESPONSE",
        message: "API response content type was not expected.",
      });
    }

    return await response.blob();
  }

  async function refreshSession(options: ApiRequestOptions): Promise<boolean> {
    const response = await fetchFn(buildUrl("/auth/refresh"), {
      credentials: "include",
      headers: refreshHeaders(options.csrfToken),
      method: "POST",
      signal: options.signal,
    });

    if (response.ok) {
      notifyAuthRefresh();
    }

    return response.ok;
  }

  return { buildUrl, fetchBinary, fetchJson };
}

const defaultTransport = createApiTransport();

export function apiFetch<TResponse>(
  path: string,
  options?: ApiRequestOptions,
): Promise<TResponse> {
  return defaultTransport.fetchJson<TResponse>(path, options);
}

export function apiFetchBinary(
  path: string,
  options: ApiBinaryRequestOptions,
): Promise<Blob> {
  return defaultTransport.fetchBinary(path, options);
}

export function buildApiUrl(path: string): string {
  return defaultTransport.buildUrl(path);
}

function normalizeBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim();

  if (trimmed.startsWith("/")) {
    return trimmed.replace(/\/+$/g, "");
  }

  const parsed = new URL(trimmed);
  parsed.pathname = "/";
  parsed.search = "";
  parsed.hash = "";
  return parsed.origin;
}

function joinApiBaseUrl(baseUrl: string, path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (baseUrl.startsWith("/")) {
    return `${baseUrl}${normalizedPath}`;
  }

  return new URL(normalizedPath, `${baseUrl}/`).toString();
}

function resolveBrowserLocalApiBaseUrl(baseUrl: string): string {
  if (typeof window === "undefined") {
    return baseUrl;
  }

  if (baseUrl.trim().startsWith("/")) {
    return baseUrl;
  }

  const parsed = new URL(baseUrl);
  const browserHostname = window.location.hostname;

  if (
    !isLoopbackHostname(browserHostname) ||
    !isLoopbackHostname(parsed.hostname) ||
    browserHostname === parsed.hostname
  ) {
    return baseUrl;
  }

  // Keep loopback host spelling aligned so SameSite cookies remain first-party.
  parsed.hostname = browserHostname;
  return parsed.toString();
}

function isLoopbackHostname(hostname: string): boolean {
  return (
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "::1" ||
    hostname === "[::1]"
  );
}

function normalizeMethod(method: string | undefined): string {
  return (method ?? "GET").toUpperCase();
}

function requestBody(options: ApiRequestOptions): BodyInit | null | undefined {
  if (options.json !== undefined) {
    return JSON.stringify(options.json);
  }

  return options.body;
}

function requestHeaders(options: ApiRequestOptions, method: string): Headers {
  const headers = new Headers(options.headers);

  if (options.json !== undefined && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }

  if (!SAFE_METHODS.has(method) && options.csrfToken) {
    headers.set(CSRF_HEADER_NAME, options.csrfToken);
  }

  return headers;
}

function refreshHeaders(csrfToken: string | null | undefined): Headers {
  const headers = new Headers();

  if (csrfToken) {
    headers.set(CSRF_HEADER_NAME, csrfToken);
  }

  return headers;
}

function notifyAuthRefresh() {
  for (const listener of authRefreshListeners) {
    listener();
  }
}

async function readJson(response: Response): Promise<unknown> {
  const rawBody = await response.text();

  if (!rawBody) {
    return undefined;
  }

  try {
    return JSON.parse(rawBody) as unknown;
  } catch {
    throw new ApiError({
      status: response.status,
      code: "INVALID_API_RESPONSE",
      message: "API response was not valid JSON.",
    });
  }
}

function responseMediaType(response: Response): string {
  return (
    response.headers
      .get("content-type")
      ?.split(";", 1)[0]
      ?.trim()
      .toLowerCase() ?? ""
  );
}
