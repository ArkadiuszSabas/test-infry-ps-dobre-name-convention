"use client";

import {
  ChevronDownIcon,
  ChevronUpIcon,
  DownloadIcon,
  PrinterIcon,
  RotateCcwIcon,
  ZoomInIcon,
  ZoomOutIcon,
} from "lucide-react";

import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";

export interface InboxPdfViewerToolbarProps {
  controlsLabel: string;
  currentPageNumber: number;
  downloadLabel: string;
  onDownload: () => void;
  onNextPage: () => void;
  onPreviousPage: () => void;
  onPrint: () => void;
  onResetZoom: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  pageLabel: string;
  pageCount: number;
  previousPageLabel: string;
  nextPageLabel: string;
  printLabel: string;
  previewAvailable: boolean;
  resetZoomLabel: string;
  scale: number;
  zoomInLabel: string;
  zoomOutLabel: string;
}

export function InboxPdfViewerToolbar({
  controlsLabel,
  currentPageNumber,
  downloadLabel,
  onDownload,
  onNextPage,
  onPreviousPage,
  onPrint,
  onResetZoom,
  onZoomIn,
  onZoomOut,
  pageLabel,
  pageCount,
  previousPageLabel,
  nextPageLabel,
  printLabel,
  previewAvailable,
  resetZoomLabel,
  scale,
  zoomInLabel,
  zoomOutLabel,
}: InboxPdfViewerToolbarProps) {
  return (
    <div className="flex shrink-0 items-center justify-between border-y px-4 py-2">
      <div
        className="flex items-center gap-1"
        aria-label={controlsLabel}
        role="group"
      >
        <IconTooltipButton
          aria-label={zoomOutLabel}
          disabled={scale <= 0.75}
          onClick={onZoomOut}
          size="icon"
          tooltip={zoomOutLabel}
          variant="ghost"
        >
          <ZoomOutIcon aria-hidden="true" />
        </IconTooltipButton>
        <span className="min-w-16 text-center text-xs tabular-nums">
          {Math.round(scale * 100)}%
        </span>
        <IconTooltipButton
          aria-label={zoomInLabel}
          disabled={scale >= 2}
          onClick={onZoomIn}
          size="icon"
          tooltip={zoomInLabel}
          variant="ghost"
        >
          <ZoomInIcon aria-hidden="true" />
        </IconTooltipButton>
        <IconTooltipButton
          aria-label={resetZoomLabel}
          onClick={onResetZoom}
          size="icon"
          tooltip={resetZoomLabel}
          variant="ghost"
        >
          <RotateCcwIcon aria-hidden="true" />
        </IconTooltipButton>
        <IconTooltipButton
          aria-label={downloadLabel}
          disabled={!previewAvailable}
          onClick={onDownload}
          size="icon"
          tooltip={downloadLabel}
          variant="ghost"
        >
          <DownloadIcon aria-hidden="true" />
        </IconTooltipButton>
        <IconTooltipButton
          aria-label={printLabel}
          disabled={!previewAvailable}
          onClick={onPrint}
          size="icon"
          tooltip={printLabel}
          variant="ghost"
        >
          <PrinterIcon aria-hidden="true" />
        </IconTooltipButton>
      </div>
      <div className="flex items-center gap-1">
        <span className="px-2 text-xs tabular-nums">{pageLabel}</span>
        <IconTooltipButton
          aria-label={previousPageLabel}
          disabled={currentPageNumber <= 1}
          onClick={onPreviousPage}
          size="icon"
          tooltip={previousPageLabel}
          variant="ghost"
        >
          <ChevronUpIcon aria-hidden="true" />
        </IconTooltipButton>
        <IconTooltipButton
          aria-label={nextPageLabel}
          disabled={currentPageNumber >= pageCount}
          onClick={onNextPage}
          size="icon"
          tooltip={nextPageLabel}
          variant="ghost"
        >
          <ChevronDownIcon aria-hidden="true" />
        </IconTooltipButton>
      </div>
    </div>
  );
}
