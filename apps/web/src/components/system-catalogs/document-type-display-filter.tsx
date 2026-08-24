"use client";

import { DocumentTypeDisplaySelect } from "@/components/system-catalogs/document-type-display-select";
import type { DocumentTypeDisplaySelectProps } from "@/components/system-catalogs/document-type-display-select";
import { cn } from "@/lib/utils";

export interface DocumentTypeDisplayFilterProps extends DocumentTypeDisplaySelectProps {
  groupClassName?: string;
}

export function DocumentTypeDisplayFilter({
  className,
  displayModeTriggerClassName,
  groupClassName,
  triggerClassName,
  ...props
}: DocumentTypeDisplayFilterProps) {
  return (
    <DocumentTypeDisplaySelect
      {...props}
      className={cn("w-full sm:w-auto", groupClassName, className)}
      displayModeTriggerClassName={cn("h-8 px-3", displayModeTriggerClassName)}
      triggerClassName={cn("h-8 min-w-56 px-3 sm:w-72", triggerClassName)}
    />
  );
}
