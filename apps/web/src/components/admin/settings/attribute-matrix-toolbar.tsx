"use client";

import { useTranslations } from "next-intl";

import {
  DataListActions,
  DataListFilters,
  DataListPanel,
  DataListToolbar,
} from "@/components/ui/data-list";
import {
  DataListChipFilter,
  DataListDropdownFilter,
  DataListSearchFilter,
} from "@/components/ui/data-list-filters";
import type { DocumentTypeDefinition } from "@/lib/admin-settings/types";
import type { SystemCatalogDefinition } from "@/lib/system-catalogs/types";

import {
  DocumentTypeSelector,
  MatrixActionButtons,
} from "./attribute-matrix-controls";

export const attributeMatrixRequirementFilters = [
  "all",
  "required",
  "optional",
  "unassigned",
] as const;

export const ALL_ATTRIBUTE_CATEGORIES_VALUE = "__all-attribute-categories";

export type AttributeMatrixRequirementFilter =
  (typeof attributeMatrixRequirementFilters)[number];

interface AttributeMatrixToolbarProps {
  attributeCategoryFilter: string;
  attributeCategoryOptions: readonly { category: string; count: number }[];
  canSave: boolean;
  definition: SystemCatalogDefinition | null;
  documentTypes: DocumentTypeDefinition[];
  documentTypesError: boolean;
  documentTypesPending: boolean;
  isDirty: boolean;
  isSaving: boolean;
  onAttributeCategoryFilterChange: (value: string) => void;
  onRequirementFilterChange: (value: string) => void;
  onReset: () => void;
  onSave: () => void;
  onSearchChange: (value: string) => void;
  onSelectDocumentType: (documentTypeId: string) => void;
  requirementFilter: AttributeMatrixRequirementFilter;
  requirementMetricCount: Record<string, number>;
  rowsCount: number;
  search: string;
  selectedDocumentTypeId: string | null;
}

export function AttributeMatrixToolbar({
  attributeCategoryFilter,
  attributeCategoryOptions,
  canSave,
  definition,
  documentTypes,
  documentTypesError,
  documentTypesPending,
  isDirty,
  isSaving,
  onAttributeCategoryFilterChange,
  onRequirementFilterChange,
  onReset,
  onSave,
  onSearchChange,
  onSelectDocumentType,
  requirementFilter,
  requirementMetricCount,
  rowsCount,
  search,
  selectedDocumentTypeId,
}: AttributeMatrixToolbarProps) {
  const t = useTranslations("AdminSettings.attributeMatrix");
  const collection = useTranslations("CollectionView");

  return (
    <DataListPanel>
      <DataListToolbar className="border-b-0">
        <DataListFilters>
          <DataListChipFilter
            ariaLabel={t("filters.requirement")}
            onValueChange={onRequirementFilterChange}
            options={attributeMatrixRequirementFilters.map((filter) => ({
              count:
                filter === "all"
                  ? rowsCount
                  : (requirementMetricCount[filter] ?? 0),
              label:
                filter === "all"
                  ? t("metrics.total.label")
                  : t(`metrics.${filter}.label`),
              value: filter,
            }))}
            value={requirementFilter}
          />

          <DocumentTypeSelector
            definition={definition}
            documentTypes={documentTypes}
            isError={documentTypesError}
            isPending={documentTypesPending}
            onSelect={onSelectDocumentType}
            selectedDocumentTypeId={selectedDocumentTypeId}
          />

          <DataListDropdownFilter
            ariaLabel={t("categories.label")}
            emptyMessage={collection("noResults")}
            onValueChange={onAttributeCategoryFilterChange}
            options={[
              {
                count: rowsCount,
                label: t("categories.all"),
                value: ALL_ATTRIBUTE_CATEGORIES_VALUE,
              },
              ...attributeCategoryOptions.map((option) => ({
                count: option.count,
                label: option.category,
                value: option.category,
              })),
            ]}
            placeholder={t("categories.label")}
            searchPlaceholder={collection("search")}
            sortOptions={false}
            value={attributeCategoryFilter}
          />

          <DataListSearchFilter
            ariaLabel={t("search")}
            onValueChange={onSearchChange}
            placeholder={t("search")}
            value={search}
          />
        </DataListFilters>

        <DataListActions>
          <MatrixActionButtons
            canSave={canSave}
            isDirty={isDirty}
            isPending={isSaving}
            onReset={onReset}
            onSave={onSave}
          />
        </DataListActions>
      </DataListToolbar>
    </DataListPanel>
  );
}
