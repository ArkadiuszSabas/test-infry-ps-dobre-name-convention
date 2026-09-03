"use client";

import { LayoutGridIcon, ListIcon } from "lucide-react";

import { DataListFilterGroup, DataListSearch } from "@/components/ui/data-list";
import {
  type SearchableSelectOption,
  SearchableSelect,
} from "@/components/ui/searchable-select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";

export interface DataListFilterOption {
  count?: number;
  description?: string;
  disabled?: boolean;
  label: string;
  value: string;
}

interface DataListChipFilterProps {
  ariaLabel: string;
  className?: string;
  onValueChange: (value: string) => void;
  options: readonly DataListFilterOption[];
  value: string;
}

export function DataListChipFilter({
  ariaLabel,
  className,
  onValueChange,
  options,
  value,
}: DataListChipFilterProps) {
  return (
    <DataListFilterGroup className={className}>
      <ToggleGroup
        aria-label={ariaLabel}
        className="flex-wrap"
        onValueChange={(nextValue) => {
          if (nextValue) {
            onValueChange(nextValue);
          }
        }}
        type="single"
        value={value}
        variant="outline"
      >
        {options.map((option) => (
          <ToggleGroupItem
            disabled={option.disabled}
            key={option.value}
            value={option.value}
          >
            {formatDataListFilterOptionLabel(option)}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </DataListFilterGroup>
  );
}

interface DataListDropdownFilterProps {
  ariaLabel: string;
  className?: string;
  disabled?: boolean;
  emptyMessage: string;
  onValueChange: (value: string) => void;
  options: readonly DataListFilterOption[];
  placeholder: string;
  searchPlaceholder: string;
  sortOptions?: boolean;
  triggerClassName?: string;
  triggerLabel?: string;
  value: string;
}

export function DataListDropdownFilter({
  ariaLabel,
  className,
  disabled = false,
  emptyMessage,
  onValueChange,
  options,
  placeholder,
  searchPlaceholder,
  sortOptions = true,
  triggerClassName,
  triggerLabel,
  value,
}: DataListDropdownFilterProps) {
  return (
    <DataListFilterGroup className={cn("min-w-0", className)}>
      <SearchableSelect
        ariaLabel={ariaLabel}
        disabled={disabled}
        emptyMessage={emptyMessage}
        onValueChange={onValueChange}
        options={options.map(toSearchableSelectOption)}
        placeholder={placeholder}
        searchPlaceholder={searchPlaceholder}
        sortOptions={sortOptions}
        triggerClassName={cn(
          "h-8 min-w-56 border-0 bg-transparent px-3 shadow-none focus-visible:ring-2 sm:w-72",
          triggerClassName,
        )}
        triggerLabel={triggerLabel}
        value={value}
      />
    </DataListFilterGroup>
  );
}

interface DataListSearchFilterProps {
  ariaLabel: string;
  className?: string;
  inputClassName?: string;
  onValueChange: (value: string) => void;
  placeholder: string;
  value: string;
}

export function DataListSearchFilter({
  ariaLabel,
  className,
  inputClassName,
  onValueChange,
  placeholder,
  value,
}: DataListSearchFilterProps) {
  return (
    <DataListFilterGroup className={className}>
      <DataListSearch
        aria-label={ariaLabel}
        inputClassName={inputClassName}
        onValueChange={onValueChange}
        placeholder={placeholder}
        value={value}
      />
    </DataListFilterGroup>
  );
}

export type DataListView = "cards" | "list";

interface DataListViewToggleProps {
  ariaLabel: string;
  cardsLabel: string;
  className?: string;
  listLabel: string;
  onValueChange: (value: DataListView) => void;
  value: DataListView;
}

export function DataListViewToggle({
  ariaLabel,
  cardsLabel,
  className,
  listLabel,
  onValueChange,
  value,
}: DataListViewToggleProps) {
  return (
    <ToggleGroup
      aria-label={ariaLabel}
      className={cn("rounded-lg border bg-background p-1 shadow-xs", className)}
      onValueChange={(nextValue) => {
        if (nextValue === "cards" || nextValue === "list") {
          onValueChange(nextValue);
        }
      }}
      spacing={0}
      type="single"
      value={value}
      variant="outline"
    >
      <ToggleGroupItem aria-label={cardsLabel} title={cardsLabel} value="cards">
        <LayoutGridIcon />
      </ToggleGroupItem>
      <ToggleGroupItem aria-label={listLabel} title={listLabel} value="list">
        <ListIcon />
      </ToggleGroupItem>
    </ToggleGroup>
  );
}

export function formatDataListFilterOptionLabel(
  option: Pick<DataListFilterOption, "count" | "label">,
): string {
  return option.count === undefined
    ? option.label
    : `${option.label} (${option.count})`;
}

function toSearchableSelectOption(
  option: DataListFilterOption,
): SearchableSelectOption {
  return {
    description: option.description,
    disabled: option.disabled,
    label: option.label,
    value: option.value,
  };
}
