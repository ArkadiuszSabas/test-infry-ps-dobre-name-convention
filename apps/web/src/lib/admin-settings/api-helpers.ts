export interface AdminCatalogRequestOptions {
  signal?: AbortSignal;
  csrfToken?: string | null;
}

export function withSearchParams(
  path: string,
  params: Record<string, string | null | undefined>,
): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value) {
      searchParams.set(key, value);
    }
  }

  const query = searchParams.toString();
  return query ? `${path}?${query}` : path;
}
