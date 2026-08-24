"use client";

import { useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { CheckIcon, ChevronDownIcon, SearchIcon } from "lucide-react";
import { Popover as PopoverPrimitive } from "radix-ui";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export interface SearchableSelectOption {
  description?: string;
  disabled?: boolean;
  label: string;
  searchText?: string;
  value: string;
}

export interface SearchableSelectProps {
  ariaLabel: string;
  className?: string;
  disabled?: boolean;
  emptyMessage: string;
  id?: string;
  invalid?: boolean;
  onValueChange: (value: string) => void;
  options: readonly SearchableSelectOption[];
  placeholder: string;
  searchPlaceholder: string;
  sortOptions?: boolean;
  triggerClassName?: string;
  value?: string;
}

export function SearchableSelect({
  ariaLabel,
  className,
  disabled = false,
  emptyMessage,
  id,
  invalid = false,
  onValueChange,
  options,
  placeholder,
  searchPlaceholder,
  sortOptions = true,
  triggerClassName,
  value,
}: SearchableSelectProps) {
  const listboxId = useId();
  const optionRefs = useRef<(HTMLDivElement | null)[]>([]);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const selectedOption = options.find((option) => option.value === value);
  const visibleOptions = useMemo(
    () => getVisibleOptions(options, search, sortOptions),
    [options, search, sortOptions],
  );

  function selectValue(nextValue: string) {
    onValueChange(nextValue);
    setOpen(false);
    setSearch("");
  }

  function closeAndFocusTrigger() {
    setOpen(false);
    window.requestAnimationFrame(() => triggerRef.current?.focus());
  }

  function enabledOptionIndexes() {
    return visibleOptions
      .map((option, index) => (option.disabled ? -1 : index))
      .filter((index) => index >= 0);
  }

  function focusOption(position: "first" | "last") {
    const indexes = enabledOptionIndexes();
    const nextIndex = position === "first" ? indexes[0] : indexes.at(-1);

    if (nextIndex !== undefined) {
      optionRefs.current[nextIndex]?.focus();
    }
  }

  function focusRelativeOption(currentIndex: number, direction: 1 | -1) {
    const indexes = enabledOptionIndexes();
    const currentPosition = indexes.indexOf(currentIndex);
    const nextIndex =
      currentPosition === -1
        ? indexes[direction === 1 ? 0 : indexes.length - 1]
        : indexes[currentPosition + direction];

    if (nextIndex !== undefined) {
      optionRefs.current[nextIndex]?.focus();
    }
  }

  function handleSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      closeAndFocusTrigger();
      return;
    }

    if (event.key === "Tab") {
      setOpen(false);
      event.stopPropagation();
      return;
    }

    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      event.stopPropagation();
      focusOption(event.key === "ArrowDown" ? "first" : "last");
      return;
    }

    if (event.key === "Enter") {
      const firstEnabledIndex = enabledOptionIndexes()[0];
      const firstEnabledOption =
        firstEnabledIndex === undefined
          ? undefined
          : visibleOptions[firstEnabledIndex];

      if (firstEnabledOption) {
        event.preventDefault();
        event.stopPropagation();
        selectValue(firstEnabledOption.value);
      }

      return;
    }

    event.stopPropagation();
  }

  function handleOptionKeyDown(
    event: KeyboardEvent<HTMLDivElement>,
    option: SearchableSelectOption,
    index: number,
  ) {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      closeAndFocusTrigger();
      return;
    }

    if (event.key === "Tab") {
      setOpen(false);
      event.stopPropagation();
      return;
    }

    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      event.stopPropagation();
      focusRelativeOption(index, event.key === "ArrowDown" ? 1 : -1);
      return;
    }

    if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      event.stopPropagation();
      focusOption(event.key === "Home" ? "first" : "last");
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      event.stopPropagation();

      if (!option.disabled) {
        selectValue(option.value);
      }
    }
  }

  return (
    <PopoverPrimitive.Root
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);

        if (nextOpen) {
          window.requestAnimationFrame(() => searchInputRef.current?.focus());
        } else {
          setSearch("");
        }
      }}
    >
      <PopoverPrimitive.Trigger asChild>
        <Button
          aria-controls={listboxId}
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-invalid={invalid}
          aria-label={ariaLabel}
          className={cn(
            "h-8 w-full justify-between gap-2 border-input bg-background px-2.5 text-left font-normal text-foreground shadow-xs aria-expanded:border-secondary/35 aria-expanded:bg-secondary/5 aria-expanded:text-secondary",
            !selectedOption && "text-muted-foreground",
            triggerClassName,
          )}
          disabled={disabled}
          id={id}
          ref={triggerRef}
          type="button"
          variant="outline"
        >
          <span className="truncate">
            {selectedOption?.label ?? placeholder}
          </span>
          <ChevronDownIcon className="size-4 text-muted-foreground" />
        </Button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="start"
          className={cn(
            "z-50 max-h-80 w-(--radix-popover-trigger-width) min-w-60 overflow-hidden rounded-lg bg-popover p-0 text-popover-foreground shadow-md ring-1 ring-foreground/10 duration-100 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95",
            className,
          )}
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            searchInputRef.current?.focus();
          }}
          sideOffset={4}
        >
          <div className="sticky top-0 z-10 bg-popover p-2">
            <div className="relative">
              <SearchIcon
                aria-hidden="true"
                className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                aria-autocomplete="list"
                aria-controls={listboxId}
                aria-expanded={open}
                aria-label={searchPlaceholder}
                autoComplete="off"
                className="h-8 pr-2 pl-8"
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={handleSearchKeyDown}
                placeholder={searchPlaceholder}
                ref={searchInputRef}
                role="combobox"
                type="search"
                value={search}
              />
            </div>
          </div>
          <div className="h-px bg-border" />
          <div
            className="max-h-60 overflow-y-auto p-1"
            id={listboxId}
            role="listbox"
          >
            {visibleOptions.length === 0 ? (
              <p className="px-2 py-3 text-center text-sm text-muted-foreground">
                {emptyMessage}
              </p>
            ) : (
              visibleOptions.map((option, index) => (
                <div
                  aria-disabled={option.disabled}
                  aria-selected={option.value === value}
                  className={cn(
                    "group/option relative flex cursor-default items-center gap-1.5 rounded-md px-1.5 py-1 text-sm outline-hidden select-none hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground aria-selected:bg-accent aria-selected:text-accent-foreground",
                    option.disabled && "pointer-events-none opacity-50",
                  )}
                  key={option.value}
                  onClick={() => {
                    if (!option.disabled) {
                      selectValue(option.value);
                    }
                  }}
                  onKeyDown={(event) =>
                    handleOptionKeyDown(event, option, index)
                  }
                  ref={(node) => {
                    optionRefs.current[index] = node;
                  }}
                  role="option"
                  tabIndex={option.disabled ? -1 : 0}
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate">{option.label}</span>
                    {option.description ? (
                      <span className="block truncate text-xs text-muted-foreground group-hover/option:text-accent-foreground group-focus/option:text-accent-foreground group-aria-selected/option:text-accent-foreground">
                        {option.description}
                      </span>
                    ) : null}
                  </span>
                  {option.value === value ? (
                    <CheckIcon className="ml-auto size-4" />
                  ) : null}
                </div>
              ))
            )}
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}

function getVisibleOptions(
  options: readonly SearchableSelectOption[],
  search: string,
  sortOptions: boolean,
): SearchableSelectOption[] {
  const normalizedSearch = search.trim().toLocaleLowerCase();
  const visibleOptions = sortOptions
    ? [...options].sort(
        (first, second) =>
          first.label.localeCompare(second.label) ||
          first.value.localeCompare(second.value),
      )
    : [...options];

  if (!normalizedSearch) {
    return visibleOptions;
  }

  return visibleOptions.filter((option) =>
    `${option.label} ${option.description ?? ""} ${option.searchText ?? ""}`
      .toLocaleLowerCase()
      .includes(normalizedSearch),
  );
}
