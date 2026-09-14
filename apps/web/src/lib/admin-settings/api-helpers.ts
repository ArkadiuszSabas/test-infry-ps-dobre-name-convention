import { toListSearchParams, type ListQuery } from "@/lib/api/list-contract";

export interface AdminCatalogRequestOptions {
  signal?: AbortSignal;
  csrfToken?: string | null;
}

export type AdminListOptions<SortField extends string> =
  AdminCatalogRequestOptions & ListQuery<SortField>;

export function withListSearchParams<
  SortField extends string,
  Options extends AdminListOptions<SortField>,
>(
  path: string,
  options: Options,
  projectFilters: (
    options: Readonly<Options>,
  ) => Record<string, string | readonly string[] | null | undefined>,
): string {
  const searchParams = toListSearchParams(options, projectFilters);
  return `${path}?${searchParams.toString()}`;
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
