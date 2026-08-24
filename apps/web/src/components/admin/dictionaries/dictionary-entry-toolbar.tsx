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
  DataListSearchFilter,
} from "@/components/ui/data-list-filters";
import type { DictionaryStatusFilter } from "@/lib/admin-settings/types";
import { catalogStatusFilters } from "@/lib/admin-settings/view-model";

interface DictionaryEntryToolbarProps {
  fieldsCount: number;
  fieldsReady: boolean;
  getEntryFilterCount: (filter: DictionaryStatusFilter) => number;
  onCreateEntry: () => void;
  onEditFields: () => void;
  onSearchChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  search: string;
  status: DictionaryStatusFilter;
}

export function DictionaryEntryToolbar({
  fieldsCount,
  fieldsReady,
  getEntryFilterCount,
  onCreateEntry,
  onEditFields,
  onSearchChange,
  onStatusChange,
  search,
  status,
}: DictionaryEntryToolbarProps) {
  const t = useTranslations("AdminSettings.customDictionaryDetail");

  return (
    <DataListToolbar>
      <DataListFilters>
        <DataListChipFilter
          ariaLabel={t("entries.columns.status")}
          onValueChange={onStatusChange}
          options={catalogStatusFilters.map((filter) => ({
            label: t(`entries.filters.${filter}`, {
              count: getEntryFilterCount(filter),
            }),
            value: filter,
          }))}
          value={status}
        />
        <DataListSearchFilter
          ariaLabel={t("entries.search")}
          onValueChange={onSearchChange}
          placeholder={t("entries.search")}
          value={search}
        />
      </DataListFilters>

      <DataListActions>
        <Button
          disabled={!fieldsReady}
          onClick={onEditFields}
          size="sm"
          variant="secondary"
        >
          <Settings2Icon data-icon="inline-start" />
          {t("fields.edit")}
        </Button>
        <Button
          disabled={!fieldsReady || fieldsCount === 0}
          onClick={onCreateEntry}
          size="sm"
        >
          <PlusIcon data-icon="inline-start" />
          {t("entries.create")}
        </Button>
      </DataListActions>
    </DataListToolbar>
  );
}
