import { ExternalLinkIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

export interface InboxPdfViewerHeaderProps {
  filename: string;
  openOriginalActionLabel: string;
  openOriginalAriaLabel: string;
  previewUrl: string | null;
  size: string;
}

export function InboxPdfViewerHeader({
  filename,
  openOriginalActionLabel,
  openOriginalAriaLabel,
  previewUrl,
  size,
}: InboxPdfViewerHeaderProps) {
  return (
    <div className="flex shrink-0 items-center justify-between gap-4 px-4 py-3">
      <span className="min-w-0 truncate text-sm font-medium">{filename}</span>
      <div className="flex shrink-0 items-center gap-2">
        <span className="text-xs text-muted-foreground">{size}</span>
        {previewUrl ? (
          <Button asChild size="sm" variant="outline">
            <a
              aria-label={openOriginalAriaLabel}
              href={previewUrl}
              rel="noreferrer"
              target="_blank"
            >
              <ExternalLinkIcon aria-hidden="true" />
              {openOriginalActionLabel}
            </a>
          </Button>
        ) : null}
      </div>
    </div>
  );
}
