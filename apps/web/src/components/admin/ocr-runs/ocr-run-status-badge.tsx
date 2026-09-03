import { Badge } from "@/components/ui/badge";
import type { OcrRunStatus } from "@/lib/admin-ocr-runs/types";
import { cn } from "@/lib/utils";

interface OcrRunStatusBadgeProps {
  label: string;
  status: OcrRunStatus;
}

export function OcrRunStatusBadge({ label, status }: OcrRunStatusBadgeProps) {
  return (
    <Badge
      className={cn(
        status === "succeeded" && "border-emerald-300 text-emerald-700",
        status === "partial_failed" && "border-amber-300 text-amber-700",
        ["failed", "cancelled"].includes(status) &&
          "border-destructive/30 text-destructive",
        ["running", "cancelling"].includes(status) &&
          "border-primary/30 text-primary",
        status === "pending" &&
          "border-muted-foreground/30 text-muted-foreground",
      )}
      variant="outline"
    >
      {label}
    </Badge>
  );
}
