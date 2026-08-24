"use client";

import { PlusIcon, Settings2Icon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  DataListActions,
  DataListFilters,
  DataListToolbar,
} from "@/components/ui/data-list";
import {
  DataListChipFilter,
  DataListDropdownFilter,
  DataListSearchFilter,
} from "@/components/ui/data-list-filters";
import type {
  CatalogListMeta,
  CatalogStatusFilter,
} from "@/lib/admin-settings/types";
import type { DocumentTypeParameterFilter } from "@/lib/admin-settings/view-model";
import {
  catalogStatusFilters,
  getCatalogStatusFilterCount,
} from "@/lib/admin-settings/view-model";

const ALL_PARAMETER_FILTER_VALUE = "all";
const PARAMETER_FILTER_VALUE_PREFIX = "value:";

interface DocumentTypeCatalogToolbarProps {
  onConfigureDefinition: () => void;
  onCreate: () => void;
  onParameterFilterChange: (code: string, value: string | null) => void;
  onSearchChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  parameterFilterValues: Readonly<Record<string, string | null | undefined>>;
  parameterFilters: readonly DocumentTypeParameterFilter[];
  search: string;
  status: CatalogStatusFilter;
  statusMeta: CatalogListMeta | undefined;
}

export function DocumentTypeCatalogToolbar({
  onConfigureDefinition,
  onCreate,
  onParameterFilterChange,
  onSearchChange,
  onStatusChange,
  parameterFilterValues,
  parameterFilters,
  search,
  status,
  statusMeta,
}: DocumentTypeCatalogToolbarProps) {
  const t = useTranslations("AdminSettings.documentTypes");
  const collection = useTranslations("CollectionView");

  return (
    <DataListToolbar>
      <DataListFilters>
        <DataListChipFilter
          ariaLabel={t("columns.status")}
          onValueChange={onStatusChange}
          options={catalogStatusFilters.map((filter) => ({
            label: t(`filters.${filter}`, {
              count: getCatalogStatusFilterCount(statusMeta, filter),
            }),
            value: filter,
          }))}
          value={status}
        />

        {parameterFilters.map((filter) => {
          const allLabel = collection("allFilter", { label: filter.label });
          const selectedValue = parameterFilterValues[filter.code];

          return (
            <DataListDropdownFilter
              ariaLabel={filter.label}
              emptyMessage={collection("noResults")}
              key={filter.code}
              onValueChange={(value) =>
                onParameterFilterChange(
                  filter.code,
                  decodeParameterFilterValue(value),
                )
              }
              options={[
                { label: allLabel, value: ALL_PARAMETER_FILTER_VALUE },
                ...filter.options.map((option) => ({
                  count: option.count,
                  label: option.value,
                  value: encodeParameterFilterValue(option.value),
                })),
              ]}
              placeholder={allLabel}
              searchPlaceholder={collection("search")}
              sortOptions={false}
              value={
                selectedValue
                  ? encodeParameterFilterValue(selectedValue)
                  : ALL_PARAMETER_FILTER_VALUE
              }
            />
          );
        })}

        <DataListSearchFilter
          ariaLabel={collection("search")}
          onValueChange={onSearchChange}
          placeholder={collection("search")}
          value={search}
        />
      </DataListFilters>

      <DataListActions>
        <Button
          onClick={onConfigureDefinition}
          size="sm"
          type="button"
          variant="outline"
        >
          <Settings2Icon data-icon="inline-start" />
          {t("configureDefinition")}
        </Button>
        <Button onClick={onCreate} size="sm">
          <PlusIcon data-icon="inline-start" />
          {t("create")}
        </Button>
      </DataListActions>
    </DataListToolbar>
  );
}

function encodeParameterFilterValue(value: string): string {
  return `${PARAMETER_FILTER_VALUE_PREFIX}${encodeURIComponent(value)}`;
}

function decodeParameterFilterValue(value: string): string | null {
  if (value === ALL_PARAMETER_FILTER_VALUE) {
    return null;
  }

  if (!value.startsWith(PARAMETER_FILTER_VALUE_PREFIX)) {
    return null;
  }

  return decodeURIComponent(value.slice(PARAMETER_FILTER_VALUE_PREFIX.length));
}
