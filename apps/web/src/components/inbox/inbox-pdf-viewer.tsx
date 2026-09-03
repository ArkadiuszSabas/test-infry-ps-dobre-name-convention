"use client";

import {
  ChevronDownIcon,
  ChevronUpIcon,
  ExternalLinkIcon,
  FileX2Icon,
  RotateCcwIcon,
  ZoomInIcon,
  ZoomOutIcon,
} from "lucide-react";
import {
  getDocument,
  GlobalWorkerOptions,
  type PDFDocumentProxy,
} from "pdfjs-dist";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useFormatter, useTranslations } from "next-intl";

import { InboxPdfPage } from "@/components/inbox/inbox-pdf-page";
import { usePdfViewerPageWindow } from "@/components/inbox/use-pdf-viewer-page-window";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { inboxClient } from "@/lib/inbox/api";
import type { InboxDocument } from "@/lib/inbox/types";
import { getNormalizedPolygonVerticalCenter } from "@/lib/review/pdf-page-geometry";
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
      scale,
    ].join("|");
  }, [navigationRequestId, scale, selectedSource]);

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

    const scrollContainer = scrollContainerRef.current;
    const targetPage = pageReferences.current.get(selectedSource.pageNumber);
    if (!scrollContainer || !targetPage) return;

    const animationFrame = window.requestAnimationFrame(() => {
      const containerBounds = scrollContainer.getBoundingClientRect();
      const targetBounds = targetPage.getBoundingClientRect();
      const sourceVerticalCenter =
        getNormalizedPolygonVerticalCenter(selectedSource.boundingPolygon) ??
        0.5;
      scrollContainer.scrollTo({
        behavior: "auto",
        top: Math.max(
          0,
          scrollContainer.scrollTop +
            targetBounds.top -
            containerBounds.top +
            targetPage.clientHeight * sourceVerticalCenter -
            scrollContainer.clientHeight / 2,
        ),
      });
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
  ]);

  return (
    <div className="flex h-full min-h-[560px] flex-col overflow-hidden bg-card lg:min-h-0">
      <div className="flex shrink-0 items-center justify-between gap-4 px-4 py-3">
        <span className="min-w-0 truncate text-sm font-medium">
          {document.originalFilename}
        </span>
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {formatFileSize(
              document.contentSizeBytes,
              format.number,
              t("unknownSize"),
            )}
          </span>
          {previewUrl ? (
            <Button asChild size="sm" variant="outline">
              <a
                aria-label={t("openOriginal", {
                  name: document.originalFilename,
                })}
                href={previewUrl}
                rel="noreferrer"
                target="_blank"
              >
                <ExternalLinkIcon aria-hidden="true" />
                {t("openOriginalAction")}
              </a>
            </Button>
          ) : null}
        </div>
      </div>
      {pdfDocument && state === "ok" ? (
        <div className="flex shrink-0 items-center justify-between border-y px-4 py-2">
          <div
            className="flex items-center gap-1"
            aria-label={t("controls.label")}
            role="group"
          >
            <Button
              aria-label={t("controls.zoomOut")}
              disabled={scale <= 0.75}
              onClick={() => setScale((value) => Math.max(0.75, value - 0.25))}
              size="icon"
              variant="ghost"
            >
              <ZoomOutIcon aria-hidden="true" />
            </Button>
            <span className="min-w-16 text-center text-xs tabular-nums">
              {Math.round(scale * 100)}%
            </span>
            <Button
              aria-label={t("controls.zoomIn")}
              disabled={scale >= 2}
              onClick={() => setScale((value) => Math.min(2, value + 0.25))}
              size="icon"
              variant="ghost"
            >
              <ZoomInIcon aria-hidden="true" />
            </Button>
            <Button
              aria-label={t("controls.resetZoom")}
              onClick={() => setScale(1)}
              size="icon"
              variant="ghost"
            >
              <RotateCcwIcon aria-hidden="true" />
            </Button>
          </div>
          <div className="flex items-center gap-1">
            <span className="px-2 text-xs tabular-nums">
              {t("controls.page", {
                current: currentPageNumber,
                total: pdfDocument.numPages,
              })}
            </span>
            <Button
              aria-label={t("controls.previousPage")}
              disabled={currentPageNumber <= 1}
              onClick={() => {
                const next = Math.max(1, currentPageNumber - 1);
                setCurrentPageNumber(next);
                pageReferences.current
                  .get(next)
                  ?.scrollIntoView({ behavior: "smooth" });
              }}
              size="icon"
              variant="ghost"
            >
              <ChevronUpIcon aria-hidden="true" />
            </Button>
            <Button
              aria-label={t("controls.nextPage")}
              disabled={currentPageNumber >= pdfDocument.numPages}
              onClick={() => {
                const next = Math.min(
                  pdfDocument.numPages,
                  currentPageNumber + 1,
                );
                setCurrentPageNumber(next);
                pageReferences.current
                  .get(next)
                  ?.scrollIntoView({ behavior: "smooth" });
              }}
              size="icon"
              variant="ghost"
            >
              <ChevronDownIcon aria-hidden="true" />
            </Button>
          </div>
        </div>
      ) : null}
      <Separator />

      <div className="relative min-h-0 flex-1 bg-background">
        {state === "loading" ? (
          <div className="absolute inset-0 flex flex-col gap-3 p-4">
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="flex-1" />
          </div>
        ) : null}

        {state === "error" ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-8 text-center text-muted-foreground">
            <FileX2Icon className="size-10 text-destructive" />
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium text-foreground">
                {t("errors.title")}
              </p>
              <p className="text-xs">{t("errors.description")}</p>
            </div>
          </div>
        ) : null}

        {pdfDocument && state === "ok" ? (
          <div
            aria-label={t("iframeTitle", { name: document.originalFilename })}
            className="h-full overflow-y-auto bg-muted/30 p-4"
            ref={scrollContainerRef}
            role="region"
          >
            <div className="mx-auto flex max-w-[1100px] flex-col gap-4">
              {Array.from({ length: pdfDocument.numPages }, (_, index) => {
                const pageNumber = index + 1;
                const pageSize = pageSizes[index];
                return (
                  <div
                    className="mx-auto"
                    key={pageNumber}
                    ref={(element) => {
                      if (element)
                        pageReferences.current.set(pageNumber, element);
                      else pageReferences.current.delete(pageNumber);
                    }}
                    style={
                      pageSize
                        ? {
                            aspectRatio: `${pageSize.width} / ${pageSize.height}`,
                            width: `${scale * 100}%`,
                          }
                        : undefined
                    }
                  >
                    {activePageNumbers.has(pageNumber) ? (
                      <InboxPdfPage
                        onError={handlePageError}
                        onPageSize={onPageSize}
                        onRendered={handlePageRendered}
                        pageNumber={pageNumber}
                        pdfDocument={pdfDocument}
                        selectedSources={selectedSources}
                      />
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
