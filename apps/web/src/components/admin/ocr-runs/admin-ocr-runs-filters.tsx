"use client";

import { CalendarDaysIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { Popover as PopoverPrimitive } from "radix-ui";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DataListFilterGroup,
  DataListFilters,
} from "@/components/ui/data-list";
import {
  DataListChipFilter,
  DataListDropdownFilter,
  DataListSearchFilter,
} from "@/components/ui/data-list-filters";
import { Input } from "@/components/ui/input";
import type {
  AdminOcrRunSummaryDto,
  OcrRunStatus,
  PublishedOcrPipelineOption,
} from "@/lib/admin-ocr-runs/types";
import {
  type AdminOcrRunDatePreset,
  type AdminOcrRunUrlState,
  adminOcrRunStatusesByView,
  buildConnectorFilterOptions,
  buildPipelineFilterOptions,
  buildSourceFilterOptions,
  getAdminOcrRunDatePresetRange,
  getAdminOcrRunStatusCount,
} from "@/lib/admin-ocr-runs/view-model";
import type { SystemCatalogOption } from "@/lib/system-catalogs/types";

const ALL_VALUE = "__all";
const datePattern = /^\d{4}-\d{2}-\d{2}$/;

interface AdminOcrRunsFiltersProps {
  documentTypes: readonly SystemCatalogOption[];
  documentTypesLoading: boolean;
  onChange: (patch: Partial<AdminOcrRunUrlState>) => void;
  pipelines: readonly PublishedOcrPipelineOption[];
  pipelinesLoading: boolean;
  runs: readonly AdminOcrRunSummaryDto[];
  state: AdminOcrRunUrlState;
}

export function AdminOcrRunsFilters({
  documentTypes,
  documentTypesLoading,
  onChange,
  pipelines,
  pipelinesLoading,
  runs,
  state,
}: AdminOcrRunsFiltersProps) {
  const t = useTranslations("AdminOcrRuns");
  const statuses = adminOcrRunStatusesByView[state.view];
  const dropdownClassName = "min-w-0 sm:w-32 sm:min-w-32";

  function optionalValue(value: string): string | undefined {
    return value === ALL_VALUE ? undefined : value;
  }

  return (
    <DataListFilters>
      <DataListChipFilter
        ariaLabel={t("filters.status")}
        className="basis-full sm:basis-auto"
        onValueChange={(value) =>
          onChange({
            offset: 0,
            status: value === ALL_VALUE ? undefined : (value as OcrRunStatus),
          })
        }
        options={[
          {
            count: getAdminOcrRunStatusCount(runs),
            label: t("filters.allStatuses"),
            value: ALL_VALUE,
          },
          ...statuses.map((status) => ({
            count: getAdminOcrRunStatusCount(runs, status),
            label: t(`statuses.${status}`),
            value: status,
          })),
        ]}
        value={state.status ?? ALL_VALUE}
      />

      <DebouncedSearchFilter
        key={state.search ?? ""}
        onChange={onChange}
        value={state.search ?? ""}
      />

      <DataListDropdownFilter
        ariaLabel={t("filters.pipeline")}
        disabled={pipelinesLoading}
        emptyMessage={t("filters.noOptions")}
        onValueChange={(value) =>
          onChange({ offset: 0, pipelineId: optionalValue(value) })
        }
        options={[
          { label: t("filters.allPipelines"), value: ALL_VALUE },
          ...buildPipelineFilterOptions(pipelines),
        ]}
        placeholder={t("filters.allPipelines")}
        searchPlaceholder={t("filters.searchOptions")}
        triggerClassName={dropdownClassName}
        triggerLabel={t("filters.pipelineShort")}
        value={state.pipelineId ?? ALL_VALUE}
      />

      <DataListDropdownFilter
        ariaLabel={t("filters.documentType")}
        disabled={documentTypesLoading}
        emptyMessage={t("filters.noOptions")}
        onValueChange={(value) =>
          onChange({ offset: 0, documentTypeId: optionalValue(value) })
        }
        options={[
          { label: t("filters.allDocumentTypes"), value: ALL_VALUE },
          ...documentTypes.map((documentType) => ({
            label: documentType.label,
            value: documentType.id,
          })),
        ]}
        placeholder={t("filters.allDocumentTypes")}
        searchPlaceholder={t("filters.searchOptions")}
        triggerClassName={dropdownClassName}
        triggerLabel={t("filters.documentTypeShort")}
        value={state.documentTypeId ?? ALL_VALUE}
      />

      <DataListDropdownFilter
        ariaLabel={t("filters.source")}
        emptyMessage={t("filters.noOptions")}
        onValueChange={(value) =>
          onChange({ offset: 0, source: optionalValue(value) })
        }
        options={[
          { label: t("filters.allSources"), value: ALL_VALUE },
          ...buildSourceFilterOptions(runs, state.source),
        ]}
        placeholder={t("filters.allSources")}
        searchPlaceholder={t("filters.searchOptions")}
        triggerClassName={dropdownClassName}
        triggerLabel={t("filters.sourceShort")}
        value={state.source ?? ALL_VALUE}
      />

      <DataListDropdownFilter
        ariaLabel={t("filters.connector")}
        emptyMessage={t("filters.noOptions")}
        onValueChange={(value) =>
          onChange({ offset: 0, connector: optionalValue(value) })
        }
        options={[
          { label: t("filters.allConnectors"), value: ALL_VALUE },
          ...buildConnectorFilterOptions(runs, state.connector),
        ]}
        placeholder={t("filters.allConnectors")}
        searchPlaceholder={t("filters.searchOptions")}
        triggerClassName={dropdownClassName}
        triggerLabel={t("filters.connectorShort")}
        value={state.connector ?? ALL_VALUE}
      />

      <DataListDropdownFilter
        ariaLabel={t("filters.stale")}
        emptyMessage={t("filters.noOptions")}
        onValueChange={(value) =>
          onChange({ offset: 0, stale: optionalValue(value) })
        }
        options={[
          { label: t("filters.anyAge"), value: ALL_VALUE },
          ...(["15m", "1h", "6h", "24h"] as const).map((value) => ({
            label: t(`filters.staleValues.${value}`),
            value,
          })),
        ]}
        placeholder={t("filters.anyAge")}
        searchPlaceholder={t("filters.searchOptions")}
        triggerClassName={dropdownClassName}
        triggerLabel={t("filters.staleShort")}
        value={state.stale ?? ALL_VALUE}
      />

      <DateRangeFilter
        key={`${state.createdFrom ?? ""}:${state.createdTo ?? ""}`}
        onChange={onChange}
        state={state}
      />
    </DataListFilters>
  );
}

function DebouncedSearchFilter({
  onChange,
  value,
}: {
  onChange: AdminOcrRunsFiltersProps["onChange"];
  value: string;
}) {
  const t = useTranslations("AdminOcrRuns");
  const [search, setSearch] = useState(value);

  useEffect(() => {
    if (search === value) return;
    const timeout = window.setTimeout(
      () => onChange({ offset: 0, search: search || undefined }),
      300,
    );
    return () => window.clearTimeout(timeout);
  }, [onChange, search, value]);

  return (
    <DataListSearchFilter
      ariaLabel={t("filters.search")}
      inputClassName="sm:w-48"
      onValueChange={setSearch}
      placeholder={t("filters.searchPlaceholder")}
      value={search}
    />
  );
}

function DateRangeFilter({
  onChange,
  state,
}: Pick<AdminOcrRunsFiltersProps, "onChange" | "state">) {
  const t = useTranslations("AdminOcrRuns");
  const [createdFrom, setCreatedFrom] = useState(state.createdFrom ?? "");
  const [createdTo, setCreatedTo] = useState(state.createdTo ?? "");

  useEffect(() => {
    const bothEmpty = !createdFrom && !createdTo;
    const bothValid =
      datePattern.test(createdFrom) && datePattern.test(createdTo);
    if (!bothEmpty && !bothValid) return;
    if (
      createdFrom === (state.createdFrom ?? "") &&
      createdTo === (state.createdTo ?? "")
    ) {
      return;
    }
    const timeout = window.setTimeout(
      () =>
        onChange({
          createdFrom: createdFrom || undefined,
          createdTo: createdTo || undefined,
          offset: 0,
        }),
      300,
    );
    return () => window.clearTimeout(timeout);
  }, [createdFrom, createdTo, onChange, state.createdFrom, state.createdTo]);

  function selectPreset(preset: AdminOcrRunDatePreset) {
    onChange({ ...getAdminOcrRunDatePresetRange(preset), offset: 0 });
  }

  const valueLabel =
    state.createdFrom || state.createdTo
      ? `${state.createdFrom ?? "…"} – ${state.createdTo ?? "…"}`
      : t("filters.dateRange");

  return (
    <DataListFilterGroup>
      <PopoverPrimitive.Root>
        <PopoverPrimitive.Trigger asChild>
          <Button
            aria-label={t("filters.dateRange")}
            className="h-8 max-w-44 justify-start border-0 bg-transparent px-3 shadow-none"
            size="sm"
            variant="ghost"
          >
            <CalendarDaysIcon />
            <span className="truncate">{valueLabel}</span>
          </Button>
        </PopoverPrimitive.Trigger>
        <PopoverPrimitive.Portal>
          <PopoverPrimitive.Content
            align="start"
            className="z-50 grid w-72 gap-3 rounded-lg border bg-popover p-3 text-popover-foreground shadow-md outline-none"
            sideOffset={6}
          >
            <div className="grid gap-1">
              {(["24h", "7d", "30d"] as const).map((preset) => (
                <Button
                  className="justify-start"
                  key={preset}
                  onClick={() => selectPreset(preset)}
                  size="sm"
                  variant="ghost"
                >
                  {t(`filters.datePresets.${preset}`)}
                </Button>
              ))}
            </div>
            <div className="border-t pt-3">
              <p className="mb-2 text-xs font-medium">
                {t("filters.datePresets.custom")}
              </p>
              <div className="grid grid-cols-2 gap-2">
                <label className="grid gap-1 text-xs text-muted-foreground">
                  {t("filters.from")}
                  <Input
                    inputMode="numeric"
                    onChange={(event) => setCreatedFrom(event.target.value)}
                    pattern="\d{4}-\d{2}-\d{2}"
                    placeholder={t("filters.datePlaceholder")}
                    value={createdFrom}
                  />
                </label>
                <label className="grid gap-1 text-xs text-muted-foreground">
                  {t("filters.to")}
                  <Input
                    inputMode="numeric"
                    onChange={(event) => setCreatedTo(event.target.value)}
                    pattern="\d{4}-\d{2}-\d{2}"
                    placeholder={t("filters.datePlaceholder")}
                    value={createdTo}
                  />
                </label>
              </div>
            </div>
          </PopoverPrimitive.Content>
        </PopoverPrimitive.Portal>
      </PopoverPrimitive.Root>
    </DataListFilterGroup>
  );
}
