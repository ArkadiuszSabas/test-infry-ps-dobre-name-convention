import type { ReviewFieldItem } from "./types";

type ReviewFieldLocation = Pick<ReviewFieldItem, "id" | "sources">;
type SearchableReviewField = Pick<ReviewFieldItem, "label" | "value">;

export function sortReviewFieldsByDocumentLocation<
  T extends ReviewFieldLocation,
>(fields: readonly T[]): T[] {
  return fields
    .map((field, index) => ({
      field,
      index,
      location: getDocumentLocation(field),
    }))
    .sort((first, second) => {
      if (first.location && second.location) {
        return (
          first.location.pageNumber - second.location.pageNumber ||
          first.location.orderIndex - second.location.orderIndex ||
          first.index - second.index
        );
      }
      if (first.location) return -1;
      if (second.location) return 1;
      return first.index - second.index;
    })
    .map(({ field }) => field);
}

export function matchesReviewFieldSearch(
  field: SearchableReviewField,
  query: string,
): boolean {
  const normalizedQuery = normalizeSearchText(query);
  if (!normalizedQuery) return true;

  return [field.label, field.value]
    .filter((value): value is string => value !== null)
    .some((value) => normalizeSearchText(value).includes(normalizedQuery));
}

function getDocumentLocation(field: ReviewFieldLocation): {
  orderIndex: number;
  pageNumber: number;
} | null {
  const locations = field.sources
    .filter(
      (source) =>
        source.pageNumber > 0 &&
        source.orderIndex >= 0 &&
        isOrderedOcrSource(source.kind),
    )
    .sort(
      (first, second) =>
        first.pageNumber - second.pageNumber ||
        first.orderIndex - second.orderIndex,
    );
  const firstLocation = locations[0];
  return firstLocation
    ? {
        pageNumber: firstLocation.pageNumber,
        orderIndex: firstLocation.orderIndex,
      }
    : null;
}

function isOrderedOcrSource(kind: string): boolean {
  return (
    kind === "ocr_key_value" ||
    kind === "ocr_key_value_pair" ||
    kind === "ocr_line"
  );
}

function normalizeSearchText(value: string): string {
  return value.trim().toLocaleLowerCase();
}
