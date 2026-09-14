"use client";

import { useCallback } from "react";

interface UsePdfViewerActionsInput {
  originalFilename: string;
  previewUrl: string | null;
}

export function usePdfViewerActions({
  originalFilename,
  previewUrl,
}: UsePdfViewerActionsInput): {
  handleDownload: () => void;
  handlePrint: () => void;
} {
  const handlePrint = useCallback(() => {
    if (!previewUrl) return;

    const printFrame = globalThis.document.createElement("iframe");
    printFrame.className =
      "pointer-events-none fixed -left-px top-0 size-px border-0 opacity-0";
    let cleanupTimeout: number | undefined;
    const cleanUpPrintFrame = () => {
      if (cleanupTimeout !== undefined) {
        window.clearTimeout(cleanupTimeout);
      }
      printFrame.remove();
    };
    const openPdfInNewTab = () => {
      window.open(previewUrl, "_blank", "noopener,noreferrer");
    };
    printFrame.addEventListener(
      "error",
      () => {
        cleanUpPrintFrame();
        openPdfInNewTab();
      },
      { once: true },
    );
    printFrame.addEventListener(
      "load",
      () => {
        try {
          const frameWindow = printFrame.contentWindow;
          if (!frameWindow) {
            cleanUpPrintFrame();
            openPdfInNewTab();
            return;
          }
          frameWindow.addEventListener("afterprint", cleanUpPrintFrame, {
            once: true,
          });
          cleanupTimeout = window.setTimeout(cleanUpPrintFrame, 60_000);
          frameWindow.focus();
          frameWindow.print();
        } catch {
          cleanUpPrintFrame();
          openPdfInNewTab();
        }
      },
      { once: true },
    );
    printFrame.src = previewUrl;
    globalThis.document.body.append(printFrame);
  }, [previewUrl]);
  const handleDownload = useCallback(() => {
    if (!previewUrl) return;

    const downloadLink = globalThis.document.createElement("a");
    downloadLink.download = originalFilename;
    downloadLink.href = previewUrl;
    globalThis.document.body.append(downloadLink);
    downloadLink.click();
    downloadLink.remove();
  }, [originalFilename, previewUrl]);

  return { handleDownload, handlePrint };
}
