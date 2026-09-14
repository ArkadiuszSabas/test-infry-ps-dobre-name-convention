"use client";

import {
  getDocument,
  GlobalWorkerOptions,
  type PDFDocumentProxy,
} from "pdfjs-dist";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useFormatter, useTranslations } from "next-intl";

import { InboxPdfViewerHeader } from "@/components/inbox/inbox-pdf-viewer-header";
import { InboxPdfViewerPages } from "@/components/inbox/inbox-pdf-viewer-pages";
import { InboxPdfViewerStatus } from "@/components/inbox/inbox-pdf-viewer-status";
import { InboxPdfViewerToolbar } from "@/components/inbox/inbox-pdf-viewer-toolbar";
import { usePdfViewerActions } from "@/components/inbox/use-pdf-viewer-actions";
import { usePdfViewerPageWindow } from "@/components/inbox/use-pdf-viewer-page-window";
import { Separator } from "@/components/ui/separator";
import { inboxClient } from "@/lib/inbox/api";
import type { InboxDocument } from "@/lib/inbox/types";
import { getNormalizedPolygonVerticalCenter } from "@/lib/review/pdf-page-geometry";
import { getPdfPageScrollBehavior } from "@/lib/review/pdf-page-window";
import type { ReviewAttributeSource } from "@/lib/review/types";
import { formatFileSize } from "@/lib/inbox/view-model";

if (typeof window !== "undefined") {
  GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.mjs",
    import.meta.url,
  ).toString();
}

export interface InboxPdfViewerProps {
  document: InboxDocument;
  navigationRequestId: number | null;
  selectedSources: readonly ReviewAttributeSource[];
  targetPageNumber: number | null;
}

type ViewerState = "loading" | "error" | "ok";

const EMPTY_RENDERED_PAGES = new Set<number>();
const PDFJS_ASSET_URLS = {
  cMapPacked: true,
  cMapUrl: "/pdfjs/cmaps/",
  iccUrl: "/pdfjs/iccs/",
  standardFontDataUrl: "/pdfjs/standard_fonts/",
  wasmUrl: "/pdfjs/wasm/",
};

interface PreviewResource {
  documentId: string;
  state: ViewerState;
  url: string | null;
}

interface LoadedPdfResource {
  document: PDFDocumentProxy;
  documentId: string;
}

interface RenderedPagesResource {
  documentId: string;
  pages: ReadonlySet<number>;
}

export function InboxPdfViewer({
  document,
  navigationRequestId,
  selectedSources,
  targetPageNumber,
}: InboxPdfViewerProps) {
  const t = useTranslations("Inbox.preview");
  const format = useFormatter();
  const [preview, setPreview] = useState<PreviewResource>({
    documentId: document.id,
    state: "loading",
    url: null,
  });
  const [loadedPdf, setLoadedPdf] = useState<LoadedPdfResource | null>(null);
  const [scale, setScale] = useState(1);
  const [currentPageNumber, setCurrentPageNumber] = useState(1);
  const [renderedPages, setRenderedPages] = useState<RenderedPagesResource>({
    documentId: document.id,
    pages: new Set(),
  });
  const pageReferences = useRef(new Map<number, HTMLDivElement>());
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const lastScrolledLayout = useRef<string | null>(null);
  const handlePageError = useCallback(() => {
    setPreview((current) =>
      current.documentId === document.id
        ? { ...current, state: "error" }
        : current,
    );
  }, [document.id]);
  const handlePageRendered = useCallback(
    (pageNumber: number) => {
      setRenderedPages((current) => {
        if (
          current.documentId === document.id &&
          current.pages.has(pageNumber)
        ) {
          return current;
        }
        const pages: Set<number> =
          current.documentId === document.id
            ? new Set<number>(current.pages)
            : new Set<number>();
        pages.add(pageNumber);
        return { documentId: document.id, pages };
      });
    },
    [document.id],
  );
  const activePreview =
    preview.documentId === document.id
      ? preview
      : { documentId: document.id, state: "loading" as const, url: null };
  const state = activePreview.state;
  const previewUrl = activePreview.url;
  const { handleDownload, handlePrint } = usePdfViewerActions({
    originalFilename: document.originalFilename,
    previewUrl,
  });
  const pdfDocument =
    loadedPdf?.documentId === document.id ? loadedPdf.document : null;
  const activeRenderedPages =
    renderedPages.documentId === document.id
      ? renderedPages.pages
      : EMPTY_RENDERED_PAGES;
  const selectedSource = useMemo(
    () =>
      targetPageNumber === null ||
      !pdfDocument ||
      targetPageNumber > pdfDocument.numPages
        ? null
        : (selectedSources.find(
            (source) => source.pageNumber === targetPageNumber,
          ) ?? null),
    [pdfDocument, selectedSources, targetPageNumber],
  );
  const selectedPageNumber = selectedSource?.pageNumber ?? null;

  const { activePageNumbers, onPageSize, pageSizes } = usePdfViewerPageWindow({
    documentId: document.id,
    onVisiblePageChange: setCurrentPageNumber,
    pageReferences,
    pdfDocument,
    scrollContainerRef,
    selectedPageNumber,
  });
  const selectedSourceLayoutKey = useMemo(() => {
    if (!selectedSource) return null;
    return [
      selectedSource.pageNumber,
      selectedSource.orderIndex,
      selectedSource.sourceKey ?? "",
      selectedSource.boundingPolygon?.join(",") ?? "",
      navigationRequestId,
    ].join("|");
  }, [navigationRequestId, selectedSource]);
  const scrollToPage = useCallback(
    (pageNumber: number, sourceVerticalCenter: number) => {
      const scrollContainer = scrollContainerRef.current;
      const targetPage = pageReferences.current.get(pageNumber);
      if (!scrollContainer || !targetPage) return;

      const containerBounds = scrollContainer.getBoundingClientRect();
      const targetBounds = targetPage.getBoundingClientRect();
      const prefersReducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;
      scrollContainer.scrollTo({
        behavior: getPdfPageScrollBehavior({
          currentPageNumber,
          prefersReducedMotion,
          targetPageNumber: pageNumber,
        }),
        top: Math.max(
          0,
          scrollContainer.scrollTop +
            targetBounds.top -
            containerBounds.top +
            targetPage.clientHeight * sourceVerticalCenter -
            scrollContainer.clientHeight / 2,
        ),
      });
    },
    [currentPageNumber],
  );
  useEffect(() => {
    if (!selectedSourceLayoutKey) lastScrolledLayout.current = null;
  }, [selectedSourceLayoutKey]);

  useEffect(() => {
    const abortController = new AbortController();
    let objectUrl: string | null = null;

    inboxClient
      .loadDocumentPdfPreview(document.id, { signal: abortController.signal })
      .then((pdfBlob) => {
        if (abortController.signal.aborted) {
          return;
        }

        objectUrl = URL.createObjectURL(pdfBlob);
        setPreview({
          documentId: document.id,
          state: "loading",
          url: objectUrl,
        });
      })
      .catch((error: unknown) => {
        if (abortController.signal.aborted) {
          return;
        }

        setPreview({
          documentId: document.id,
          state: "error",
          url: null,
        });
        console.warn("Document PDF preview failed to load.", {
          documentId: document.id,
          error,
        });
      });

    return () => {
      abortController.abort();
      if (objectUrl !== null) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [document.id]);

  useEffect(() => {
    if (!previewUrl) return;

    const loadingTask = getDocument({
      url: previewUrl,
      ...PDFJS_ASSET_URLS,
    });
    let cancelled = false;

    void loadingTask.promise
      .then((loadedDocument) => {
        if (cancelled) {
          return;
        }
        setLoadedPdf({ document: loadedDocument, documentId: document.id });
        setPreview((current) =>
          current.documentId === document.id
            ? { ...current, state: "ok" }
            : current,
        );
      })
      .catch(() => {
        if (!cancelled) {
          setPreview((current) =>
            current.documentId === document.id
              ? { ...current, state: "error" }
              : current,
          );
        }
      });

    return () => {
      cancelled = true;
      void loadingTask.destroy();
    };
  }, [document.id, previewUrl]);

  useEffect(() => {
    if (
      !selectedSource ||
      !selectedSourceLayoutKey ||
      !pdfDocument ||
      pageSizes.length !== pdfDocument.numPages ||
      !activePageNumbers.has(selectedSource.pageNumber) ||
      !activeRenderedPages.has(selectedSource.pageNumber)
    ) {
      return;
    }

    if (lastScrolledLayout.current === selectedSourceLayoutKey) return;

    const animationFrame = window.requestAnimationFrame(() => {
      const sourceVerticalCenter =
        getNormalizedPolygonVerticalCenter(selectedSource.boundingPolygon) ??
        0.5;
      scrollToPage(selectedSource.pageNumber, sourceVerticalCenter);
      lastScrolledLayout.current = selectedSourceLayoutKey;
    });

    return () => window.cancelAnimationFrame(animationFrame);
  }, [
    activePageNumbers,
    activeRenderedPages,
    pageSizes.length,
    pdfDocument,
    selectedSource,
    selectedSourceLayoutKey,
    scrollToPage,
  ]);

  return (
    <div className="flex h-full min-h-[560px] flex-col overflow-hidden bg-card lg:min-h-0">
      <InboxPdfViewerHeader
        filename={document.originalFilename}
        openOriginalActionLabel={t("openOriginalAction")}
        openOriginalAriaLabel={t("openOriginal", {
          name: document.originalFilename,
        })}
        previewUrl={previewUrl}
        size={formatFileSize(
          document.contentSizeBytes,
          format.number,
          t("unknownSize"),
        )}
      />
      {pdfDocument && state === "ok" ? (
        <InboxPdfViewerToolbar
          controlsLabel={t("controls.label")}
          currentPageNumber={currentPageNumber}
          downloadLabel={t("controls.download")}
          nextPageLabel={t("controls.nextPage")}
          onDownload={handleDownload}
          onNextPage={() => {
            const next = Math.min(pdfDocument.numPages, currentPageNumber + 1);
            setCurrentPageNumber(next);
            scrollToPage(next, 0.5);
          }}
          onPreviousPage={() => {
            const next = Math.max(1, currentPageNumber - 1);
            setCurrentPageNumber(next);
            scrollToPage(next, 0.5);
          }}
          onPrint={handlePrint}
          onResetZoom={() => setScale(1)}
          onZoomIn={() => setScale((value) => Math.min(2, value + 0.25))}
          onZoomOut={() => setScale((value) => Math.max(0.75, value - 0.25))}
          pageCount={pdfDocument.numPages}
          pageLabel={t("controls.page", {
            current: currentPageNumber,
            total: pdfDocument.numPages,
          })}
          previousPageLabel={t("controls.previousPage")}
          previewAvailable={previewUrl !== null}
          printLabel={t("controls.print")}
          resetZoomLabel={t("controls.resetZoom")}
          scale={scale}
          zoomInLabel={t("controls.zoomIn")}
          zoomOutLabel={t("controls.zoomOut")}
        />
      ) : null}
      <Separator />

      <div className="relative min-h-0 flex-1 bg-background">
        <InboxPdfViewerStatus
          errorDescription={t("errors.description")}
          errorTitle={t("errors.title")}
          state={state}
        />

        {pdfDocument && state === "ok" ? (
          <InboxPdfViewerPages
            activePageNumbers={activePageNumbers}
            filename={t("iframeTitle", { name: document.originalFilename })}
            onPageError={handlePageError}
            onPageRendered={handlePageRendered}
            onPageSize={onPageSize}
            pageReferences={pageReferences}
            pageSizes={pageSizes}
            pdfDocument={pdfDocument}
            scale={scale}
            scrollContainerRef={scrollContainerRef}
            selectedSources={selectedSources}
          />
        ) : null}
      </div>
    </div>
  );
}
