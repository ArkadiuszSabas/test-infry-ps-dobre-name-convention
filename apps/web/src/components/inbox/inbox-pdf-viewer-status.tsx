import { FileX2Icon } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";

type PdfViewerState = "loading" | "error" | "ok";

export interface InboxPdfViewerStatusProps {
  errorDescription: string;
  errorTitle: string;
  state: PdfViewerState;
}

export function InboxPdfViewerStatus({
  errorDescription,
  errorTitle,
  state,
}: InboxPdfViewerStatusProps) {
  if (state === "loading") {
    return (
      <div className="absolute inset-0 flex flex-col gap-3 p-4">
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="flex-1" />
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-8 text-center text-muted-foreground">
        <FileX2Icon className="size-10 text-destructive" />
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium text-foreground">{errorTitle}</p>
          <p className="text-xs">{errorDescription}</p>
        </div>
      </div>
    );
  }

  return null;
}
