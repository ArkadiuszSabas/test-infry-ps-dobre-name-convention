export const LIST_DEFAULT_LIMIT = 50;
export const LIST_MAX_LIMIT = 200;
export const LIST_SEARCH_DEBOUNCE_MS = 300;
export const LIST_SEARCH_MAX_LENGTH = 200;

export type ListSortDirection = "asc" | "desc";
export type ListFilterValue =
  | boolean
  | number
  | string
  | null
  | undefined
  | readonly (boolean | number | string)[];

export type ListQuery<
  SortField extends string,
  Filters extends object = Record<never, never>,
> = {
  search?: string;
  sortBy: SortField;
  sortDirection: ListSortDirection;
  limit: number;
  offset: number;
} & Filters;

export interface ListQueryConfig<SortField extends string> {
  defaultLimit?: number;
  defaultSortBy: SortField;
  defaultSortDirection?: ListSortDirection;
  maxLimit?: number;
  sortFields: readonly SortField[];
}

export interface ListPageMetaDto {
  total: number;
  returned_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface ListPageMeta {
  total: number;
  returnedCount: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export interface ListPage<Data, Meta extends ListPageMeta = ListPageMeta> {
  data: Data;
  meta: Meta;
}

export type ListPresentationState =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "empty" }
  | { kind: "ready"; isRefreshing: boolean };

export function parseListQuery<SortField extends string>(
  params: Pick<URLSearchParams, "get">,
  config: ListQueryConfig<SortField>,
): ListQuery<SortField> {
  const defaultLimit = config.defaultLimit ?? LIST_DEFAULT_LIMIT;
  const maxLimit = config.maxLimit ?? LIST_MAX_LIMIT;
  const requestedSort = params.get("sort_by");
  const sortBy =
    config.sortFields.find((field) => field === requestedSort) ??
    config.defaultSortBy;

  return {
    ...normalizedSearch(params.get("search")),
    limit: parseBoundedInteger(params.get("limit"), defaultLimit, 1, maxLimit),
    offset: parseBoundedInteger(
      params.get("offset"),
      0,
      0,
      Number.MAX_SAFE_INTEGER,
    ),
    sortBy,
    sortDirection: parseSortDirection(
      params.get("sort_direction"),
      config.defaultSortDirection ?? "asc",
    ),
  };
}

export function toListSearchParams<
  SortField extends string,
  Filters extends object,
>(
  query: ListQuery<SortField, Filters>,
  projectFilters: (
    query: Readonly<ListQuery<SortField, Filters>>,
  ) => Readonly<Record<string, ListFilterValue>>,
): URLSearchParams {
  const params = new URLSearchParams({
    limit: String(query.limit),
    offset: String(query.offset),
    sort_by: query.sortBy,
    sort_direction: query.sortDirection,
  });
  const search = query.search?.trim();
  if (search) params.set("search", search.slice(0, LIST_SEARCH_MAX_LENGTH));
  const filters = projectFilters(query);
  for (const [name, value] of Object.entries(filters).sort(([a], [b]) =>
    a.localeCompare(b),
  )) {
    appendFilter(params, name, value);
  }
  return params;
}

export function buildListQueryKey<Query extends object>(
  prefix: readonly unknown[],
  query: Query,
): readonly unknown[] {
  return [...prefix, query] as const;
}

export function updateListQuery<Query extends { offset: number }>(
  query: Query,
  patch: Partial<Query>,
): Query {
  const resetsOffset = Object.keys(patch).some((key) => key !== "offset");
  return { ...query, ...patch, ...(resetsOffset ? { offset: 0 } : {}) };
}

export function mapListPageMeta(meta: ListPageMetaDto): ListPageMeta {
  return {
    hasMore: meta.has_more,
    limit: meta.limit,
    offset: meta.offset,
    returnedCount: meta.returned_count,
    total: meta.total,
  };
}

export function getListPresentationState(input: {
  hasError: boolean;
  isFetching: boolean;
  isPending: boolean;
  returnedCount: number;
}): ListPresentationState {
  if (input.isPending) return { kind: "loading" };
  if (input.hasError) return { kind: "error" };
  if (input.returnedCount === 0) return { kind: "empty" };
  return { kind: "ready", isRefreshing: input.isFetching };
}

function appendFilter(
  params: URLSearchParams,
  name: string,
  value: ListFilterValue,
): void {
  if (value === null || value === undefined || value === "") return;
  if (Array.isArray(value)) {
    for (const item of value) params.append(name, String(item));
    return;
  }
  params.set(name, String(value));
}

function normalizedSearch(
  search: string | null,
): Pick<ListQuery<string>, "search"> {
  const normalized = search?.trim().slice(0, LIST_SEARCH_MAX_LENGTH);
  return normalized ? { search: normalized } : {};
}

function parseSortDirection(
  value: string | null,
  fallback: ListSortDirection,
): ListSortDirection {
  return value === "asc" || value === "desc" ? value : fallback;
}

function parseBoundedInteger(
  value: string | null,
  fallback: number,
  minimum: number,
  maximum: number,
): number {
  if (value === null || value.trim() === "") return fallback;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= minimum && parsed <= maximum
    ? parsed
    : fallback;
}
