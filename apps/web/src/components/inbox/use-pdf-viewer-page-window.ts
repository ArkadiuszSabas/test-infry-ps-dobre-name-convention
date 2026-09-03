import type { PDFDocumentProxy } from "pdfjs-dist";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type RefObject,
} from "react";

import {
  createEstimatedPdfPageSizes,
  getActivePdfPageNumbers,
  getNearbyPdfPageNumbers,
  getVisiblePdfPageNumber,
  type PdfPageSize,
} from "@/lib/review/pdf-page-window";

const EMPTY_PAGE_SIZES: readonly PdfPageSize[] = [];
const MAX_NEARBY_RENDERED_PAGES = 3;
const PAGE_RENDER_BUFFER_PIXELS = 480;

interface PdfPageSizesResource {
  documentId: string;
  sizes: ReadonlyMap<number, PdfPageSize>;
}

interface UsePdfViewerPageWindowInput {
  documentId: string;
  onVisiblePageChange: (pageNumber: number) => void;
  pageReferences: RefObject<Map<number, HTMLDivElement>>;
  pdfDocument: PDFDocumentProxy | null;
  scrollContainerRef: RefObject<HTMLDivElement | null>;
  selectedPageNumber: number | null;
}

export function usePdfViewerPageWindow({
  documentId,
  onVisiblePageChange,
  pageReferences,
  pdfDocument,
  scrollContainerRef,
  selectedPageNumber,
}: UsePdfViewerPageWindowInput): {
  activePageNumbers: ReadonlySet<number>;
  onPageSize: (pageNumber: number, size: PdfPageSize) => void;
  pageSizes: readonly PdfPageSize[];
} {
  const [pageSizesResource, setPageSizesResource] =
    useState<PdfPageSizesResource>({
      documentId,
      sizes: new Map(),
    });
  const [nearbyPageNumbers, setNearbyPageNumbers] = useState<
    ReadonlySet<number>
  >(() => new Set());
  const pageSizes = useMemo(() => {
    if (!pdfDocument) return EMPTY_PAGE_SIZES;

    const sizes = [...createEstimatedPdfPageSizes(pdfDocument.numPages)];
    if (pageSizesResource.documentId !== documentId) return sizes;

    for (const [pageNumber, size] of pageSizesResource.sizes) {
      sizes[pageNumber - 1] = size;
    }
    return sizes;
  }, [documentId, pageSizesResource, pdfDocument]);
  const onPageSize = useCallback(
    (pageNumber: number, size: PdfPageSize) => {
      setPageSizesResource((current) => {
        const currentSize =
          current.documentId === documentId
            ? current.sizes.get(pageNumber)
            : undefined;
        if (
          currentSize &&
          currentSize.height === size.height &&
          currentSize.width === size.width
        ) {
          return current;
        }
        const sizes =
          current.documentId === documentId
            ? new Map(current.sizes)
            : new Map<number, PdfPageSize>();
        sizes.set(pageNumber, size);
        return { documentId, sizes };
      });
    },
    [documentId],
  );

  useEffect(() => {
    const scrollContainer = scrollContainerRef.current;
    if (
      !scrollContainer ||
      !pdfDocument ||
      pageSizes.length !== pdfDocument.numPages
    ) {
      return;
    }

    let animationFrame: number | null = null;
    const updateNearbyPages = () => {
      animationFrame = null;
      const containerBounds = scrollContainer.getBoundingClientRect();
      const pageBounds = Array.from(pageReferences.current.entries()).map(
        ([pageNumber, page]) => {
          const bounds = page.getBoundingClientRect();
          return { bottom: bounds.bottom, pageNumber, top: bounds.top };
        },
      );
      const visiblePageNumber = getVisiblePdfPageNumber({
        pageBounds,
        viewportBottom: containerBounds.bottom,
        viewportTop: containerBounds.top,
      });
      if (visiblePageNumber !== null) {
        onVisiblePageChange(visiblePageNumber);
      }
      const pageNumbers = getNearbyPdfPageNumbers({
        bufferPixels: PAGE_RENDER_BUFFER_PIXELS,
        maximumPageCount: MAX_NEARBY_RENDERED_PAGES,
        pageBounds,
        viewportBottom: containerBounds.bottom,
        viewportTop: containerBounds.top,
      });

      setNearbyPageNumbers((current) => {
        const next = new Set(pageNumbers);
        return samePageSet(current, next) ? current : next;
      });
    };
    const scheduleNearbyPageUpdate = () => {
      if (animationFrame === null) {
        animationFrame = window.requestAnimationFrame(updateNearbyPages);
      }
    };

    scheduleNearbyPageUpdate();
    scrollContainer.addEventListener("scroll", scheduleNearbyPageUpdate, {
      passive: true,
    });
    const resizeObserver = new ResizeObserver(scheduleNearbyPageUpdate);
    resizeObserver.observe(scrollContainer);

    return () => {
      scrollContainer.removeEventListener("scroll", scheduleNearbyPageUpdate);
      resizeObserver.disconnect();
      if (animationFrame !== null) {
        window.cancelAnimationFrame(animationFrame);
      }
    };
  }, [
    onVisiblePageChange,
    pageReferences,
    pageSizes,
    pdfDocument,
    scrollContainerRef,
  ]);

  const activePageNumbers = useMemo(
    () => getActivePdfPageNumbers(nearbyPageNumbers, selectedPageNumber),
    [nearbyPageNumbers, selectedPageNumber],
  );

  return { activePageNumbers, onPageSize, pageSizes };
}

function samePageSet(
  first: ReadonlySet<number>,
  second: ReadonlySet<number>,
): boolean {
  return (
    first.size === second.size &&
    Array.from(first).every((pageNumber) => second.has(pageNumber))
  );
}
