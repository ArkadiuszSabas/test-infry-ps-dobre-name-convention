const DEFAULT_DOCMIND_API_BASE_URL = "/api/docmind";

export interface PublicConfig {
  docmindApiBaseUrl: string;
  isEntraLoginEnabled: boolean;
}

export function getPublicConfig(): PublicConfig {
  return {
    docmindApiBaseUrl: normalizeApiBaseUrl(
      process.env.NEXT_PUBLIC_DOCMIND_API_BASE_URL ??
        DEFAULT_DOCMIND_API_BASE_URL,
    ),
    isEntraLoginEnabled: parsePublicBoolean(
      process.env.NEXT_PUBLIC_DOCMIND_AUTH_ENTRA_ID_ENABLED,
      "NEXT_PUBLIC_DOCMIND_AUTH_ENTRA_ID_ENABLED",
    ),
  };
}

function normalizeApiBaseUrl(value: string): string {
  const trimmed = value.trim();

  if (!trimmed) {
    return DEFAULT_DOCMIND_API_BASE_URL;
  }

  if (trimmed.startsWith("/")) {
    return normalizeRelativeApiBasePath(trimmed);
  }

  const parsed = new URL(trimmed);

  if (parsed.pathname !== "/" || parsed.search || parsed.hash) {
    throw new Error(
      "NEXT_PUBLIC_DOCMIND_API_BASE_URL must be an API origin or root-relative path without query or hash.",
    );
  }

  return parsed.origin;
}

function normalizeRelativeApiBasePath(value: string): string {
  if (value.startsWith("//")) {
    throw new Error(
      "NEXT_PUBLIC_DOCMIND_API_BASE_URL must be an API origin or root-relative path without query or hash.",
    );
  }

  const parsed = new URL(value, "http://docmind-web.local");

  if (parsed.search || parsed.hash || parsed.pathname === "/") {
    throw new Error(
      "NEXT_PUBLIC_DOCMIND_API_BASE_URL must be an API origin or root-relative path without query or hash.",
    );
  }

  return parsed.pathname.replace(/\/+$/g, "");
}

function parsePublicBoolean(value: string | undefined, name: string): boolean {
  if (value === undefined || value.trim() === "") {
    return false;
  }

  const normalized = value.trim().toLowerCase();

  if (normalized === "true") {
    return true;
  }

  if (normalized === "false") {
    return false;
  }

  throw new Error(`${name} must be true or false.`);
}
