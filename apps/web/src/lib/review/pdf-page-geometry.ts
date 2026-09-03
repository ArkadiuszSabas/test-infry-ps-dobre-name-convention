import type { ReviewAttributeSource } from "@/lib/review/types";
import { isReviewSourceLocatable } from "@/lib/review/source-location";

export interface PdfPageSize {
  height: number;
  width: number;
}

export interface PdfPolygonGeometry extends PdfPageSize {
  points: string;
}

/**
 * Converts a normalized OCR polygon into the CSS-pixel coordinate system of
 * one rendered PDF page. The caller owns validation of OCR source data.
 */
export function toPdfPolygonGeometry(
  normalizedPolygon: readonly number[] | null,
  pageSize: PdfPageSize,
): PdfPolygonGeometry | null {
  if (
    !normalizedPolygon ||
    normalizedPolygon.length < 8 ||
    normalizedPolygon.length > 16 ||
    normalizedPolygon.length % 2 !== 0 ||
    !isPositiveFinite(pageSize.width) ||
    !isPositiveFinite(pageSize.height) ||
    normalizedPolygon.some(
      (coordinate) =>
        !Number.isFinite(coordinate) || coordinate < 0 || coordinate > 1,
    )
  ) {
    return null;
  }

  const points: string[] = [];
  for (let index = 0; index < normalizedPolygon.length; index += 2) {
    points.push(
      `${normalizedPolygon[index]! * pageSize.width},${normalizedPolygon[index + 1]! * pageSize.height}`,
    );
  }

  return { ...pageSize, points: points.join(" ") };
}

/** Maps every renderable source on one page into PDF overlay geometry. */
export function toPdfPagePolygonGeometries(
  sources: readonly ReviewAttributeSource[],
  pageNumber: number,
  pageSize: PdfPageSize,
): PdfPolygonGeometry[] {
  return sources.flatMap((source) => {
    if (!isReviewSourceLocatable(source) || source.pageNumber !== pageNumber)
      return [];

    const polygon = toPdfPolygonGeometry(source.boundingPolygon, pageSize);
    return polygon ? [polygon] : [];
  });
}

/** Returns the vertical midpoint of a valid normalized source polygon. */
export function getNormalizedPolygonVerticalCenter(
  normalizedPolygon: readonly number[] | null,
): number | null {
  if (
    !normalizedPolygon ||
    normalizedPolygon.length < 8 ||
    normalizedPolygon.length > 16 ||
    normalizedPolygon.length % 2 !== 0 ||
    normalizedPolygon.some(
      (coordinate) =>
        !Number.isFinite(coordinate) || coordinate < 0 || coordinate > 1,
    )
  ) {
    return null;
  }

  const yCoordinates = normalizedPolygon.filter((_, index) => index % 2 === 1);
  const minimum = Math.min(...yCoordinates);
  const maximum = Math.max(...yCoordinates);
  return (minimum + maximum) / 2;
}

function isPositiveFinite(value: number): boolean {
  return Number.isFinite(value) && value > 0;
}
