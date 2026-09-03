export interface PdfPageWindowBounds {
  bottom: number;
  pageNumber: number;
  top: number;
}

export interface PdfPageSize {
  height: number;
  width: number;
}

const ESTIMATED_PAGE_SIZE: PdfPageSize = { height: 792, width: 612 };

export function createEstimatedPdfPageSizes(
  pageCount: number,
): readonly PdfPageSize[] {
  return Array.from({ length: pageCount }, () => ESTIMATED_PAGE_SIZE);
}

export function getActivePdfPageNumbers(
  nearbyPageNumbers: ReadonlySet<number>,
  selectedPageNumber: number | null,
): ReadonlySet<number> {
  const pageNumbers = new Set(nearbyPageNumbers);
  if (selectedPageNumber !== null) pageNumbers.add(selectedPageNumber);
  return pageNumbers;
}

export function getNearbyPdfPageNumbers({
  bufferPixels,
  maximumPageCount,
  pageBounds,
  viewportBottom,
  viewportTop,
}: {
  bufferPixels: number;
  maximumPageCount: number;
  pageBounds: readonly PdfPageWindowBounds[];
  viewportBottom: number;
  viewportTop: number;
}): number[] {
  const viewportCenter = (viewportTop + viewportBottom) / 2;
  return pageBounds
    .filter(
      (page) =>
        page.bottom >= viewportTop - bufferPixels &&
        page.top <= viewportBottom + bufferPixels,
    )
    .sort(
      (first, second) =>
        Math.abs((first.top + first.bottom) / 2 - viewportCenter) -
        Math.abs((second.top + second.bottom) / 2 - viewportCenter),
    )
    .slice(0, maximumPageCount)
    .map((page) => page.pageNumber);
}

export function getVisiblePdfPageNumber({
  pageBounds,
  viewportBottom,
  viewportTop,
}: {
  pageBounds: readonly PdfPageWindowBounds[];
  viewportBottom: number;
  viewportTop: number;
}): number | null {
  const viewportCenter = (viewportTop + viewportBottom) / 2;
  const visiblePages = pageBounds
    .map((page) => ({
      ...page,
      distanceFromViewportCenter: Math.abs(
        (page.top + page.bottom) / 2 - viewportCenter,
      ),
      visibleHeight: Math.max(
        0,
        Math.min(page.bottom, viewportBottom) - Math.max(page.top, viewportTop),
      ),
    }))
    .filter((page) => page.visibleHeight > 0)
    .sort(
      (first, second) =>
        second.visibleHeight - first.visibleHeight ||
        first.distanceFromViewportCenter - second.distanceFromViewportCenter,
    );

  return visiblePages[0]?.pageNumber ?? null;
}
