"use client";

import type { PDFDocumentProxy } from "pdfjs-dist";
import type { RefObject } from "react";

import { InboxPdfPage } from "@/components/inbox/inbox-pdf-page";
import type { PdfPageSize } from "@/lib/review/pdf-page-window";
import type { ReviewAttributeSource } from "@/lib/review/types";

export interface InboxPdfViewerPagesProps {
  activePageNumbers: ReadonlySet<number>;
  filename: string;
  onPageError: () => void;
  onPageRendered: (pageNumber: number) => void;
  onPageSize: (pageNumber: number, pageSize: PdfPageSize) => void;
  pageReferences: RefObject<Map<number, HTMLDivElement>>;
  pageSizes: readonly PdfPageSize[];
  pdfDocument: PDFDocumentProxy;
  scale: number;
  scrollContainerRef: RefObject<HTMLDivElement | null>;
  selectedSources: readonly ReviewAttributeSource[];
}

export function InboxPdfViewerPages({
  activePageNumbers,
  filename,
  onPageError,
  onPageRendered,
  onPageSize,
  pageReferences,
  pageSizes,
  pdfDocument,
  scale,
  scrollContainerRef,
  selectedSources,
}: InboxPdfViewerPagesProps) {
  return (
    <div
      aria-label={filename}
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
                if (element) pageReferences.current.set(pageNumber, element);
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
                  onError={onPageError}
                  onPageSize={onPageSize}
                  onRendered={onPageRendered}
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
  );
}
