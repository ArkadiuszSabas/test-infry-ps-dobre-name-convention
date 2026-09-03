import {
  CheckCircle2Icon,
  CircleDashedIcon,
  Clock3Icon,
  RefreshCwIcon,
  XCircleIcon,
} from "lucide-react";

import type {
  OcrPipelineRunStatus,
  OcrPipelineRunStepStatus,
} from "@/lib/inbox/types";
import { cn } from "@/lib/utils";

export function StepStatusIcon({
  status,
}: {
  status: OcrPipelineRunStepStatus;
}) {
  const className = cn("mt-0.5 size-4 shrink-0", stepIconClassName(status));

  switch (status) {
    case "succeeded":
      return <CheckCircle2Icon className={className} />;
    case "failed":
      return <XCircleIcon className={className} />;
    case "running":
      return <RefreshCwIcon className={cn(className, "animate-spin")} />;
    case "skipped":
      return <Clock3Icon className={className} />;
    case "pending":
      return <CircleDashedIcon className={className} />;
    default:
      return <CircleDashedIcon className={className} />;
  }
}

export function runStatusClassName(status: OcrPipelineRunStatus): string {
  switch (status) {
    case "succeeded":
      return "border-emerald-300 text-emerald-700";
    case "partial_failed":
      return "border-amber-300 text-amber-700";
    case "failed":
    case "cancelled":
      return "border-destructive/30 text-destructive";
    case "running":
    case "cancelling":
      return "border-primary/30 text-primary";
    case "pending":
      return "border-muted-foreground/30 text-muted-foreground";
    default:
      return "border-muted-foreground/30 text-muted-foreground";
  }
}

export function stepStatusClassName(status: OcrPipelineRunStepStatus): string {
  switch (status) {
    case "succeeded":
      return "border-emerald-300 text-emerald-700";
    case "failed":
      return "border-destructive/30 text-destructive";
    case "running":
      return "border-primary/30 text-primary";
    case "skipped":
      return "border-amber-300 text-amber-700";
    case "pending":
      return "border-muted-foreground/30 text-muted-foreground";
    default:
      return "border-muted-foreground/30 text-muted-foreground";
  }
}

function stepIconClassName(status: OcrPipelineRunStepStatus): string {
  switch (status) {
    case "succeeded":
      return "text-emerald-600";
    case "failed":
      return "text-destructive";
    case "running":
      return "text-primary";
    case "skipped":
      return "text-amber-600";
    case "pending":
      return "text-muted-foreground";
    default:
      return "text-muted-foreground";
  }
}
