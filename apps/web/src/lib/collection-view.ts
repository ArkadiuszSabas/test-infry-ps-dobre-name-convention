export type SortDirection = "asc" | "desc";

export type SortValue = boolean | Date | number | string | null | undefined;

export interface SortState<ColumnId extends string> {
  column: ColumnId;
  direction: SortDirection;
}

interface SortOptions<T> {
  accessor: (item: T) => SortValue;
  direction?: SortDirection;
}

interface CollectionViewOptions<T> {
  search?: string;
  searchAccessors?: readonly ((item: T) => SortValue)[];
  sort?: SortOptions<T> | null;
}

export function nextSortState<ColumnId extends string>(
  current: SortState<ColumnId>,
  column: ColumnId,
): SortState<ColumnId> {
  if (current.column !== column) {
    return { column, direction: "asc" };
  }

  return {
    column,
    direction: current.direction === "asc" ? "desc" : "asc",
  };
}

export function applyCollectionView<T>(
  items: readonly T[],
  options: CollectionViewOptions<T>,
): T[] {
  const filtered = filterItemsBySearch(
    items,
    options.search ?? "",
    options.searchAccessors ?? [],
  );

  if (!options.sort) {
    return filtered;
  }

  return sortItems(filtered, options.sort.accessor, options.sort.direction);
}

export function filterItemsBySearch<T>(
  items: readonly T[],
  search: string,
  accessors: readonly ((item: T) => SortValue)[],
): T[] {
  const normalizedSearch = normalizeSearchText(search);

  if (!normalizedSearch || accessors.length === 0) {
    return [...items];
  }

  return items.filter((item) =>
    accessors.some((accessor) =>
      normalizeSearchText(valueToSearchText(accessor(item))).includes(
        normalizedSearch,
      ),
    ),
  );
}

export function sortItems<T>(
  items: readonly T[],
  accessor: (item: T) => SortValue,
  direction: SortDirection = "asc",
): T[] {
  return items
    .map((item, index) => ({ index, item }))
    .sort((first, second) => {
      const compared = compareSortValues(
        accessor(first.item),
        accessor(second.item),
        direction,
      );

      return compared || first.index - second.index;
    })
    .map(({ item }) => item);
}

export function compareSortValues(
  first: SortValue,
  second: SortValue,
  direction: SortDirection = "asc",
): number {
  const firstComparable = toComparableValue(first);
  const secondComparable = toComparableValue(second);

  if (firstComparable === null && secondComparable === null) {
    return 0;
  }

  if (firstComparable === null) {
    return 1;
  }

  if (secondComparable === null) {
    return -1;
  }

  const multiplier = direction === "asc" ? 1 : -1;

  if (
    typeof firstComparable === "number" &&
    typeof secondComparable === "number"
  ) {
    return (firstComparable - secondComparable) * multiplier;
  }

  return (
    String(firstComparable).localeCompare(String(secondComparable)) * multiplier
  );
}

export function normalizeSearchText(value: string): string {
  return value.trim().toLocaleLowerCase();
}

function valueToSearchText(value: SortValue): string {
  if (value === null || value === undefined) {
    return "";
  }

  if (value instanceof Date) {
    return value.toISOString();
  }

  return String(value);
}

function toComparableValue(value: SortValue): number | string | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  if (value instanceof Date) {
    return value.getTime();
  }

  if (typeof value === "boolean") {
    return value ? 1 : 0;
  }

  if (typeof value === "number") {
    return value;
  }

  const normalized = value.trim();
  const dateValue = toIsoDateValue(normalized);

  return dateValue ?? normalized.toLocaleLowerCase();
}

function toIsoDateValue(value: string): number | null {
  if (!/^\d{4}-\d{2}-\d{2}(?:T|\b)/u.test(value)) {
    return null;
  }

  const timestamp = Date.parse(value);

  return Number.isNaN(timestamp) ? null : timestamp;
}
