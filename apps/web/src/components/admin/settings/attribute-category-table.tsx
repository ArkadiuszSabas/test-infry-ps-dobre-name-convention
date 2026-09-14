"use client";

import { Edit3Icon, PowerIcon, Trash2Icon } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import {
  CatalogStatusBadge,
  LoadingTableRows,
} from "@/components/admin/catalog/catalog-shared";
import { Button } from "@/components/ui/button";
import { DataListRow, DataListTable } from "@/components/ui/data-list";
import {
  SortableTableHead,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TruncatedTableText,
} from "@/components/ui/table";
import { TableEmptyState } from "@/components/ui/table-empty-state";
import type { AttributeCategory } from "@/lib/admin-settings/types";
import type { AttributeCategorySortField } from "@/lib/admin-settings/attribute-api";
import { nextSortState, type SortState } from "@/lib/collection-view";

import { AttributeCategoryFlagBadges } from "./attribute-category-flag-badges";

const DEFAULT_ATTRIBUTE_CATEGORY_EXTERNAL_ID = "bez_kategorii";
interface AttributeCategoryTableProps {
  categories: AttributeCategory[];
  emptyDescription?: string;
  emptyTitle?: string;
  isError: boolean;
  isPending: boolean;
  onDeactivate: (category: AttributeCategory) => void;
  onDelete: (category: AttributeCategory) => void;
  onEdit: (category: AttributeCategory) => void;
  onSortChange: (sort: SortState<AttributeCategorySortField>) => void;
  sort: SortState<AttributeCategorySortField>;
}

export function AttributeCategoryTable({
  categories,
  emptyDescription,
  emptyTitle,
  isError,
  isPending,
  onDeactivate,
  onDelete,
  onEdit,
  onSortChange,
  sort,
}: AttributeCategoryTableProps) {
  const t = useTranslations("AdminSettings.attributeCategories");
  const common = useTranslations("AdminSettings.common");
  const collection = useTranslations("CollectionView");
  const format = useFormatter();
  function sortLabel(column: AttributeCategorySortField, label: string) {
    const nextDirection =
      sort.column === column && sort.direction === "asc" ? "desc" : "asc";

    return collection(`sort.${nextDirection}`, { column: label });
  }

  return (
    <DataListTable>
      <TableHeader>
        <TableRow className="border-0 hover:bg-transparent">
          <SortableTableHead
            active={sort.column === "label"}
            direction={sort.direction}
            onSort={() => onSortChange(nextSortState(sort, "label"))}
            sortLabel={sortLabel("label", t("columns.name"))}
          >
            {t("columns.name")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "flags"}
            direction={sort.direction}
            onSort={() => onSortChange(nextSortState(sort, "flags"))}
            sortLabel={sortLabel("flags", t("columns.flags"))}
          >
            {t("columns.flags")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "status"}
            direction={sort.direction}
            onSort={() => onSortChange(nextSortState(sort, "status"))}
            sortLabel={sortLabel("status", t("columns.status"))}
          >
            {t("columns.status")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "updated_at"}
            direction={sort.direction}
            onSort={() => onSortChange(nextSortState(sort, "updated_at"))}
            sortLabel={sortLabel("updated_at", t("columns.updatedAt"))}
          >
            {t("columns.updatedAt")}
          </SortableTableHead>
          <TableHead className="text-right">{t("columns.actions")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {isPending ? <LoadingTableRows columns={5} /> : null}
        {!isPending && !isError && categories.length === 0 ? (
          <TableEmptyState
            columns={5}
            description={emptyDescription ?? t("emptyDescription")}
            title={emptyTitle ?? t("emptyTitle")}
          />
        ) : null}
        {categories.map((category) => {
          const isDefaultCategory =
            category.externalId === DEFAULT_ATTRIBUTE_CATEGORY_EXTERNAL_ID;

          return (
            <DataListRow key={category.id}>
              <TableCell className="w-[32%] font-medium">
                <div className="flex min-w-0 flex-col gap-1">
                  <TruncatedTableText value={category.label} />
                  <TruncatedTableText
                    className="font-mono text-xs text-muted-foreground"
                    value={category.externalId}
                  />
                </div>
              </TableCell>
              <TableCell>
                <AttributeCategoryFlagBadges
                  emptyLabel={common("notSet")}
                  flags={category.flags}
                  isMetadataLabel={t("flags.isMetadata")}
                />
              </TableCell>
              <TableCell>
                <CatalogStatusBadge
                  label={common(`status.${category.status}`)}
                  status={category.status}
                />
              </TableCell>
              <TableCell>
                {format.dateTime(new Date(category.updatedAt), {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                })}
              </TableCell>
              <TableCell>
                <div className="flex justify-end gap-1">
                  <Button
                    aria-label={t("actions.edit", { name: category.label })}
                    onClick={() => onEdit(category)}
                    size="icon-sm"
                    type="button"
                    variant="secondary"
                  >
                    <Edit3Icon />
                  </Button>
                  <Button
                    aria-label={t("actions.deactivate", {
                      name: category.label,
                    })}
                    disabled={
                      category.status === "inactive" || isDefaultCategory
                    }
                    onClick={() => onDeactivate(category)}
                    size="icon-sm"
                    type="button"
                    variant="secondary"
                  >
                    <PowerIcon />
                  </Button>
                  <Button
                    aria-label={t("actions.delete", { name: category.label })}
                    disabled={isDefaultCategory}
                    onClick={() => onDelete(category)}
                    size="icon-sm"
                    type="button"
                    variant="secondary"
                  >
                    <Trash2Icon />
                  </Button>
                </div>
              </TableCell>
            </DataListRow>
          );
        })}
      </TableBody>
    </DataListTable>
  );
}
