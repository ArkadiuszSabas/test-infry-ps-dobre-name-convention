"use client";

import { ChevronDownIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";

interface CatalogFormSectionProps {
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  defaultOpen?: boolean;
  description?: ReactNode;
  summary?: ReactNode;
  title: ReactNode;
}

export function CatalogFormSection({
  children,
  className,
  contentClassName,
  defaultOpen = false,
  description,
  summary,
  title,
}: CatalogFormSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className={cn("rounded-lg border bg-background", className)}>
      <button
        aria-expanded={open}
        className="flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-3 text-left"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold">{title}</span>
          {description ? (
            <span className="block text-sm text-muted-foreground">
              {description}
            </span>
          ) : null}
        </span>
        <span className="flex min-w-0 shrink items-center gap-2 text-xs font-normal text-muted-foreground">
          {summary ? <span className="min-w-0 truncate">{summary}</span> : null}
          <ChevronDownIcon
            aria-hidden="true"
            className={cn(
              "shrink-0 transition-transform",
              open ? "rotate-180" : null,
            )}
            data-icon="inline-end"
          />
        </span>
      </button>
      {open ? (
        <div className={cn("border-t px-4 py-4", contentClassName)}>
          {children}
        </div>
      ) : null}
    </section>
  );
}
