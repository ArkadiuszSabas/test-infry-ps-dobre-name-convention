"use client";

import { FileX2Icon } from "lucide-react";
import { useEffect, useState } from "react";
import { useFormatter, useTranslations } from "next-intl";

import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { inboxClient } from "@/lib/inbox/api";
import type { InboxDocument } from "@/lib/inbox/types";
import { formatFileSize, getInboxPreviewState } from "@/lib/inbox/view-model";
import { cn } from "@/lib/utils";

export interface InboxPdfViewerProps {
  document: InboxDocument;
}

type ViewerState = "loading" | "error" | "ok";

interface PreviewResource {
  documentId: string;
  state: ViewerState;
  url: string | null;
}

export function InboxPdfViewer({ document }: InboxPdfViewerProps) {
  const t = useTranslations("Inbox.preview");
  const format = useFormatter();
  const [preview, setPreview] = useState<PreviewResource>({
    documentId: document.id,
    state: "loading",
    url: null,
  });
  const activePreview =
    preview.documentId === document.id
      ? preview
      : { documentId: document.id, state: "loading" as const, url: null };
  const state = activePreview.state;
  const previewUrl = activePreview.url;
  const previewState = getInboxPreviewState(previewUrl);

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

  return (
    <div className="flex h-full min-h-[560px] flex-col overflow-hidden bg-card lg:min-h-0">
      <div className="flex shrink-0 items-center justify-between gap-4 px-4 py-3">
        <span className="min-w-0 truncate text-sm font-medium">
          {document.originalFilename}
        </span>
        <span className="shrink-0 text-xs text-muted-foreground">
          {formatFileSize(
            document.contentSizeBytes,
            format.number,
            t("unknownSize"),
          )}
        </span>
      </div>
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

        {previewState.kind === "available" && state !== "error" ? (
          <iframe
            className={cn(
              "h-full w-full border-0 bg-background",
              state !== "ok" && "invisible",
            )}
            onError={() =>
              setPreview((current) =>
                current.documentId === document.id
                  ? { ...current, state: "error" }
                  : current,
              )
            }
            onLoad={() =>
              setPreview((current) =>
                current.documentId === document.id
                  ? { ...current, state: "ok" }
                  : current,
              )
            }
            src={previewState.url}
            title={t("iframeTitle", { name: document.name })}
          />
        ) : null}
      </div>
    </div>
  );
}
