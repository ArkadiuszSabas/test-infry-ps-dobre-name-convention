"use client";

import { useMemo, useState } from "react";

import { SearchableSelect } from "@/components/ui/searchable-select";
import type { SearchableSelectOption } from "@/components/ui/searchable-select";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  formatDocumentTypeDisplayLabel,
  getDocumentTypeDisplayModeOptions,
  resolveDocumentTypeDisplayModeId,
  shouldShowDocumentTypeDisplayModeSelect,
  sortDocumentTypeDisplayItems,
  type DocumentTypeDisplayItem,
} from "@/lib/system-catalogs/document-type-display";
import type { SystemCatalogDefinition } from "@/lib/system-catalogs/types";
import { cn } from "@/lib/utils";

export interface DocumentTypeDisplaySelectProps {
  ariaLabel: string;
  className?: string;
  definition?: SystemCatalogDefinition | null;
  disabled?: boolean;
  displayModeAriaLabel?: string;
  displayModeClassName?: string;
  displayModePlaceholder?: string;
  displayModeTriggerClassName?: string;
  emptyMessage: string;
  id?: string;
  invalid?: boolean;
  onDisplayModeChange?: (displayModeId: string) => void;
  onValueChange: (value: string) => void;
  options: readonly DocumentTypeDisplayItem[];
  placeholder: string;
  searchPlaceholder: string;
  triggerClassName?: string;
  value?: string;
}

export function DocumentTypeDisplaySelect({
  ariaLabel,
  className,
  definition,
  disabled = false,
  displayModeAriaLabel,
  displayModeClassName,
  displayModePlaceholder,
  displayModeTriggerClassName,
  emptyMessage,
  id,
  invalid = false,
  onDisplayModeChange,
  onValueChange,
  options,
  placeholder,
  searchPlaceholder,
  triggerClassName,
  value,
}: DocumentTypeDisplaySelectProps) {
  const [internalDisplayModeId, setInternalDisplayModeId] = useState<
    string | null
  >(null);
  const effectiveDisplayModeId = resolveDocumentTypeDisplayModeId({
    definition,
    preferredDisplayModeId: internalDisplayModeId,
  });
  const selectOptions = useMemo(
    () =>
      sortDocumentTypeDisplayItems({
        definition,
        displayModeId: effectiveDisplayModeId,
        documentTypes: options,
      }).map(
        (option): SearchableSelectOption => ({
          label: formatDocumentTypeDisplayLabel({
            definition,
            displayModeId: effectiveDisplayModeId,
            documentType: option,
          }),
          searchText: documentTypeSearchText(option),
          value: option.id,
        }),
      ),
    [definition, effectiveDisplayModeId, options],
  );
  const modeOptions = useMemo(
    () => getDocumentTypeDisplayModeOptions(definition),
    [definition],
  );
  const showDisplayModeSelect =
    shouldShowDocumentTypeDisplayModeSelect(definition);

  function changeDisplayMode(displayModeId: string) {
    setInternalDisplayModeId(displayModeId);
    onDisplayModeChange?.(displayModeId);
  }

  return (
    <div
      className={cn(
        "flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-1 shadow-xs sm:flex-row sm:items-center",
        className,
      )}
    >
      <SearchableSelect
        ariaLabel={ariaLabel}
        disabled={disabled}
        emptyMessage={emptyMessage}
        id={id}
        invalid={invalid}
        onValueChange={onValueChange}
        options={selectOptions}
        placeholder={placeholder}
        searchPlaceholder={searchPlaceholder}
        sortOptions={false}
        triggerClassName={cn(
          "border-0 bg-transparent shadow-none focus-visible:ring-2",
          triggerClassName,
        )}
        value={value}
      />

      {showDisplayModeSelect ? (
        <>
          <span
            aria-hidden="true"
            className="hidden h-6 w-px shrink-0 bg-border sm:block"
          />
          <Select
            disabled={disabled}
            onValueChange={changeDisplayMode}
            value={effectiveDisplayModeId ?? undefined}
          >
            <SelectTrigger
              aria-label={
                displayModeAriaLabel ?? displayModePlaceholder ?? ariaLabel
              }
              className={cn(
                "min-w-36 border-0 bg-transparent shadow-none focus-visible:ring-2",
                displayModeTriggerClassName,
              )}
            >
              <SelectValue placeholder={displayModePlaceholder} />
            </SelectTrigger>
            <SelectContent className={displayModeClassName}>
              <SelectGroup>
                {modeOptions.map((mode) => (
                  <SelectItem key={mode.id} value={mode.id}>
                    {mode.label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </>
      ) : null}
    </div>
  );
}

function documentTypeSearchText(option: DocumentTypeDisplayItem): string {
  return [
    option.displayLabel,
    option.label,
    option.name,
    option.externalId,
    ...(option.parameters ?? []).flatMap((parameter) => [
      parameter.label,
      parameter.value,
    ]),
    ...(option.extensionValues ?? []).flatMap((extensionValue) => [
      extensionValue.displayValue,
      extensionValue.textValue,
    ]),
  ]
    .filter((value): value is string => Boolean(value?.trim()))
    .join(" ");
}
