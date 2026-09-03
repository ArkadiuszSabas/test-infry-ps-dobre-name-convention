"use client";

import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import {
  toPdfPagePolygonGeometries,
  type PdfPolygonGeometry,
} from "@/lib/review/pdf-page-geometry";
import type { PdfPageSize } from "@/lib/review/pdf-page-window";
import type { ReviewAttributeSource } from "@/lib/review/types";

interface PageViewportSize {
  height: number;
  width: number;
}

export interface InboxPdfPageProps {
  onError: () => void;
  onRendered: (pageNumber: number) => void;
  onPageSize: (pageNumber: number, size: PdfPageSize) => void;
  pageNumber: number;
  pdfDocument: PDFDocumentProxy;
  selectedSources: readonly ReviewAttributeSource[];
}

export function InboxPdfPage({
  onError,
  onRendered,
  onPageSize,
  pageNumber,
  pdfDocument,
  selectedSources,
}: InboxPdfPageProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [availableWidth, setAvailableWidth] = useState(0);
  const [viewport, setViewport] = useState<PageViewportSize | null>(null);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const updateWidth = () => setAvailableWidth(container.clientWidth);
    updateWidth();
    const resizeObserver = new ResizeObserver(updateWidth);
    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    if (!availableWidth) return;

    let cancelled = false;
    let renderTask: RenderTask | null = null;

    void pdfDocument
      .getPage(pageNumber)
      .then((page) => {
        if (cancelled) return;

        const baseViewport = page.getViewport({ scale: 1 });
        onPageSize(pageNumber, {
          height: baseViewport.height,
          width: baseViewport.width,
        });
        const pageViewport = page.getViewport({
          scale: availableWidth / baseViewport.width,
        });
        const canvas = canvasRef.current;
        const context = canvas?.getContext("2d");
        if (!canvas || !context) {
          throw new Error("PDF page canvas is unavailable.");
        }

        const outputScale = window.devicePixelRatio || 1;
        canvas.width = Math.floor(pageViewport.width * outputScale);
        canvas.height = Math.floor(pageViewport.height * outputScale);
        canvas.style.width = `${pageViewport.width}px`;
        canvas.style.height = `${pageViewport.height}px`;
        setViewport({ height: pageViewport.height, width: pageViewport.width });

        renderTask = page.render({
          canvas,
          canvasContext: context,
          transform: [outputScale, 0, 0, outputScale, 0, 0],
          viewport: pageViewport,
        });
        return renderTask.promise;
      })
      .then(() => {
        if (!cancelled) onRendered(pageNumber);
      })
      .catch(() => {
        if (!cancelled) onError();
      });

    return () => {
      cancelled = true;
      renderTask?.cancel();
    };
  }, [
    availableWidth,
    onError,
    onPageSize,
    onRendered,
    pageNumber,
    pdfDocument,
  ]);

  const polygons = useMemo<PdfPolygonGeometry[]>(() => {
    if (!viewport) return [];

    return toPdfPagePolygonGeometries(selectedSources, pageNumber, viewport);
  }, [pageNumber, selectedSources, viewport]);

  return (
    <div className="relative w-full" ref={containerRef}>
      <canvas
        className="block h-auto w-full bg-white shadow-sm"
        ref={canvasRef}
      />
      {polygons.length > 0 ? (
        <svg
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 h-full w-full"
          preserveAspectRatio="none"
          viewBox={`0 0 ${polygons[0].width} ${polygons[0].height}`}
        >
          {polygons.map((polygon, index) => (
            <polygon
              className="fill-yellow-300/45 stroke-yellow-500"
              key={`${index}-${polygon.points}`}
              points={polygon.points}
              strokeWidth="2"
            />
          ))}
        </svg>
      ) : null}
    </div>
  );
}
