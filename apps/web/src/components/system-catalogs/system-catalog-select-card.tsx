"use client";

import type { LucideIcon } from "lucide-react";
import { FileTextIcon } from "lucide-react";
import { useMemo } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { IconFrame } from "@/components/ui/icon-frame";
import { DocumentTypeDisplaySelect } from "@/components/system-catalogs/document-type-display-select";
import {
  sortDocumentTypeDisplayItems,
  type DocumentTypeDisplayItem,
} from "@/lib/system-catalogs/document-type-display";
import type { SystemCatalogDefinition } from "@/lib/system-catalogs/types";

interface SystemCatalogSelectCardLabels {
  displayModeLabel?: string;
  displayModePlaceholder?: string;
  noOptions: string;
  searchPlaceholder?: string;
  valueLabel: string;
  valuePlaceholder: string;
}

export interface SystemCatalogSelectCardProps {
  catalogKey: string;
  definition?: SystemCatalogDefinition | null;
  description?: string;
  disabled?: boolean;
  icon?: LucideIcon;
  labels: SystemCatalogSelectCardLabels;
  onValueChange: (value: string) => void;
  options: readonly DocumentTypeDisplayItem[];
  title: string;
  value: string;
}

export function SystemCatalogSelectCard({
  catalogKey,
  definition,
  description,
  disabled = false,
  icon = FileTextIcon,
  labels,
  onValueChange,
  options,
  title,
  value,
}: SystemCatalogSelectCardProps) {
  const sortedOptions = useMemo(
    () =>
      sortDocumentTypeDisplayItems({
        definition,
        documentTypes: options,
      }),
    [definition, options],
  );

  return (
    <Card data-catalog-key={catalogKey}>
      <CardHeader className="border-b">
        <div className="flex min-w-0 items-start gap-3">
          <IconFrame icon={icon} size="sm" />
          <div className="min-w-0">
            <CardTitle>{title}</CardTitle>
            {description ? (
              <CardDescription>{description}</CardDescription>
            ) : null}
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 pt-4">
        <div className="grid gap-4">
          <label className="flex min-w-0 flex-col gap-2 text-sm font-medium">
            {labels.valueLabel}
            {sortedOptions.length > 0 ? (
              <DocumentTypeDisplaySelect
                ariaLabel={labels.valueLabel}
                definition={definition}
                disabled={disabled}
                displayModeAriaLabel={labels.displayModeLabel}
                displayModePlaceholder={labels.displayModePlaceholder}
                emptyMessage={labels.noOptions}
                onValueChange={onValueChange}
                options={sortedOptions}
                placeholder={labels.valuePlaceholder}
                searchPlaceholder={
                  labels.searchPlaceholder ?? labels.valuePlaceholder
                }
                displayModeTriggerClassName="w-full justify-between px-2.5 sm:w-40"
                triggerClassName="min-w-0 flex-1 px-2.5"
                value={value || undefined}
              />
            ) : (
              <span className="flex h-8 items-center rounded-lg border bg-muted/30 px-3 text-sm text-muted-foreground">
                {labels.noOptions}
              </span>
            )}
          </label>
        </div>
      </CardContent>
    </Card>
  );
}
