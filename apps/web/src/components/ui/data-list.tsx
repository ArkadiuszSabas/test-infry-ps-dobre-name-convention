import type { ComponentProps } from "react";
import { SearchIcon } from "lucide-react";

import { CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PanelCard } from "@/components/ui/panel-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableCell, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

function DataListPanel({
  className,
  ...props
}: ComponentProps<typeof PanelCard>) {
  return <PanelCard className={cn("gap-0 py-0", className)} {...props} />;
}

function DataListToolbar({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="data-list-toolbar"
      className={cn(
        "flex flex-col gap-3 border-b bg-muted/20 p-5 lg:flex-row lg:items-start lg:justify-between",
        className,
      )}
      {...props}
    />
  );
}

function DataListFilters({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="data-list-filters"
      className={cn(
        "flex min-w-0 flex-1 flex-wrap items-start gap-2",
        className,
      )}
      {...props}
    />
  );
}

function DataListFilterGroup({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="data-list-filter-group"
      className={cn("rounded-lg border bg-background p-1 shadow-xs", className)}
      {...props}
    />
  );
}

function DataListSearch({
  className,
  inputClassName,
  onValueChange,
  value,
  ...props
}: Omit<ComponentProps<typeof Input>, "onChange" | "value"> & {
  inputClassName?: string;
  onValueChange: (value: string) => void;
  value: string;
}) {
  return (
    <div
      className={cn(
        "relative min-w-0 rounded-lg focus-within:ring-3 focus-within:ring-ring/50",
        className,
      )}
    >
      <SearchIcon
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
      />
      <Input
        className={cn(
          "h-8 w-full min-w-44 border-0 pr-3 pl-8 shadow-none focus-visible:ring-0 sm:w-64",
          inputClassName,
        )}
        onChange={(event) => onValueChange(event.target.value)}
        type="search"
        value={value}
        {...props}
      />
    </div>
  );
}

function DataListActions({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="data-list-actions"
      className={cn(
        "flex max-w-full shrink-0 flex-wrap items-center gap-2 self-start rounded-lg border bg-background p-1 shadow-xs [&_[data-slot=button]]:h-8",
        className,
      )}
      {...props}
    />
  );
}

function DataListContent({
  className,
  ...props
}: ComponentProps<typeof CardContent>) {
  return (
    <CardContent
      className={cn("flex flex-col gap-4 p-5", className)}
      {...props}
    />
  );
}

function DataListTable({ className, ...props }: ComponentProps<typeof Table>) {
  return (
    <Table
      className={cn(
        "table-fixed border-separate border-spacing-y-2",
        className,
      )}
      {...props}
    />
  );
}

function DataListRow({ className, ...props }: ComponentProps<typeof TableRow>) {
  return (
    <TableRow
      className={cn(
        "border-0 bg-card shadow-[var(--shadow-card)] hover:bg-accent/60 [&>td]:border-y [&>td]:border-border/70 [&>td:first-child]:rounded-l-lg [&>td:first-child]:border-l [&>td:last-child]:rounded-r-lg [&>td:last-child]:border-r",
        className,
      )}
      {...props}
    />
  );
}

function DataListGrid({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="data-list-grid"
      className={cn("grid gap-3 md:grid-cols-2 xl:grid-cols-3", className)}
      {...props}
    />
  );
}

function DataListSkeletonRows({
  columns,
  rows = 4,
}: {
  columns: number;
  rows?: number;
}) {
  return Array.from({ length: rows }, (_, rowIndex) => (
    <DataListRow key={rowIndex}>
      {Array.from({ length: columns }, (__, columnIndex) => (
        <TableCell key={columnIndex}>
          <Skeleton className="h-5 w-full max-w-36" />
        </TableCell>
      ))}
    </DataListRow>
  ));
}

export {
  DataListActions,
  DataListContent,
  DataListFilterGroup,
  DataListFilters,
  DataListGrid,
  DataListPanel,
  DataListRow,
  DataListSearch,
  DataListSkeletonRows,
  DataListTable,
  DataListToolbar,
};
