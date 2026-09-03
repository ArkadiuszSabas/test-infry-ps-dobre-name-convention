import type {
  ReviewAttributeSource,
  ReviewFieldItem,
} from "@/lib/review/types";

type SourceAwareReviewField = Pick<
  ReviewFieldItem,
  "kind" | "manuallyEdited" | "sources"
>;

/** Returns the sources that can be safely located and highlighted in the PDF. */
export function getLocatableReviewSources(
  sources: readonly ReviewAttributeSource[],
): ReviewAttributeSource[] {
  return sources
    .map((source, index) => ({ index, source }))
    .filter(({ source }) => isReviewSourceLocatable(source))
    .sort(
      (first, second) =>
        first.source.pageNumber - second.source.pageNumber ||
        first.source.orderIndex - second.source.orderIndex ||
        first.index - second.index,
    )
    .map(({ source }) => source);
}

/** Returns OCR fragment sources suitable for stable field ordering. */
export function getOrderedReviewSources(
  sources: readonly ReviewAttributeSource[],
): ReviewAttributeSource[] {
  return sources
    .map((source, index) => ({ index, source }))
    .filter(({ source }) => isReviewSourceOrdered(source))
    .sort(
      (first, second) =>
        first.source.pageNumber - second.source.pageNumber ||
        first.source.orderIndex - second.source.orderIndex ||
        first.index - second.index,
    )
    .map(({ source }) => source);
}

/** Excludes manual values because their OCR provenance no longer identifies their value. */
export function getReviewFieldLocatableSources(
  field: SourceAwareReviewField,
): ReviewAttributeSource[] {
  if (field.kind === "manual" || field.manuallyEdited) return [];

  return getLocatableReviewSources(field.sources);
}

export function isReviewSourceLocatable(
  source: ReviewAttributeSource,
): boolean {
  const polygon = source.boundingPolygon;
  return (
    isFragmentSourceKind(source.kind) &&
    source.coordinateSystem === "normalized_0_1" &&
    Number.isInteger(source.pageNumber) &&
    source.pageNumber > 0 &&
    Number.isFinite(source.orderIndex) &&
    source.orderIndex >= 0 &&
    polygon !== null &&
    polygon.length >= 8 &&
    polygon.length <= 16 &&
    polygon.length % 2 === 0 &&
    polygon.every((coordinate) => Number.isFinite(coordinate)) &&
    polygon.every((coordinate) => coordinate >= 0 && coordinate <= 1)
  );
}

function isReviewSourceOrdered(source: ReviewAttributeSource): boolean {
  return (
    isOrderedSourceKind(source.kind) &&
    Number.isInteger(source.pageNumber) &&
    source.pageNumber > 0 &&
    Number.isFinite(source.orderIndex) &&
    source.orderIndex >= 0
  );
}

function isOrderedSourceKind(kind: string): boolean {
  return (
    kind === "ocr_key_value" ||
    kind === "ocr_key_value_pair" ||
    kind === "ocr_line"
  );
}

/** Document-level OCR has no trustworthy fragment location for highlighting. */
function isFragmentSourceKind(kind: string): boolean {
  return (
    kind === "ocr_key_value" ||
    kind === "ocr_key_value_pair" ||
    kind === "ocr_line" ||
    kind === "ocr_selection_mark" ||
    kind === "ocr_table_cell"
  );
}
