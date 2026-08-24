"use client";

import { useMemo, useState } from "react";
import { Edit3Icon, PowerIcon, Trash2Icon } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import {
  CatalogStatusBadge,
  LoadingTableRows,
} from "@/components/admin/catalog/catalog-shared";
import { Badge } from "@/components/ui/badge";
import { DataListRow, DataListTable } from "@/components/ui/data-list";
import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import { TableEmptyState } from "@/components/ui/table-empty-state";
import {
  SortableTableHead,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TruncatedTableText,
} from "@/components/ui/table";
import type {
  AttributeDefinition,
  AttributeStatusFilter,
} from "@/lib/admin-settings/types";
import { filterAttributesByStatus } from "@/lib/admin-settings/view-model";
import {
  applyCollectionView,
  nextSortState,
  type SortState,
  type SortValue,
} from "@/lib/collection-view";

type AttributeSortColumn =
  | "category"
  | "name"
  | "schema"
  | "status"
  | "updatedAt";

const attributeSortAccessors: Record<
  AttributeSortColumn,
  (attribute: AttributeDefinition) => SortValue
> = {
  category: (attribute) => attribute.category,
  name: (attribute) => attribute.name,
  schema: (attribute) =>
    `${attribute.dataType} ${attribute.source} ${attribute.valueSource} ${attribute.schemaVersion}`,
  status: (attribute) => attribute.status,
  updatedAt: (attribute) => attribute.updatedAt,
};

interface AttributeCatalogTableProps {
  attributes: readonly AttributeDefinition[];
  isError: boolean;
  isPending: boolean;
  onDeactivate: (attribute: AttributeDefinition) => void;
  onDelete: (attribute: AttributeDefinition) => void;
  onEdit: (attribute: AttributeDefinition) => void;
  search: string;
  status: AttributeStatusFilter;
}

export function AttributeCatalogTable({
  attributes,
  isError,
  isPending,
  onDeactivate,
  onDelete,
  onEdit,
  search,
  status,
}: AttributeCatalogTableProps) {
  const t = useTranslations("AdminSettings.attributes");
  const common = useTranslations("AdminSettings.common");
  const collection = useTranslations("CollectionView");
  const format = useFormatter();
  const [sort, setSort] = useState<SortState<AttributeSortColumn>>({
    column: "name",
    direction: "asc",
  });
  const visibleAttributes = useMemo(
    () =>
      applyCollectionView(filterAttributesByStatus(attributes, status), {
        search,
        searchAccessors: [
          (attribute): SortValue => attribute.name,
          (attribute): SortValue => attribute.category,
          (attribute): SortValue => attribute.comment,
          (attribute): SortValue => attribute.externalId,
        ],
        sort: {
          accessor: attributeSortAccessors[sort.column],
          direction: sort.direction,
        },
      }),
    [attributes, search, sort, status],
  );
  const hasSearch = search.trim().length > 0;

  function sortLabel(column: AttributeSortColumn, label: string) {
    const nextDirection =
      sort.column === column && sort.direction === "asc" ? "desc" : "asc";

    return collection(`sort.${nextDirection}`, { column: label });
  }

  return (
    <DataListTable>
      <TableHeader>
        <TableRow className="border-0 hover:bg-transparent">
          <SortableTableHead
            active={sort.column === "name"}
            className="w-[26%]"
            direction={sort.direction}
            onSort={() => setSort((current) => nextSortState(current, "name"))}
            sortLabel={sortLabel("name", t("columns.name"))}
          >
            {t("columns.name")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "category"}
            className="w-[16%]"
            direction={sort.direction}
            onSort={() =>
              setSort((current) => nextSortState(current, "category"))
            }
            sortLabel={sortLabel("category", t("columns.category"))}
          >
            {t("columns.category")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "schema"}
            className="w-[22%]"
            direction={sort.direction}
            onSort={() =>
              setSort((current) => nextSortState(current, "schema"))
            }
            sortLabel={sortLabel("schema", t("columns.schema"))}
          >
            {t("columns.schema")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "status"}
            className="w-24"
            direction={sort.direction}
            onSort={() =>
              setSort((current) => nextSortState(current, "status"))
            }
            sortLabel={sortLabel("status", t("columns.status"))}
          >
            {t("columns.status")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "updatedAt"}
            className="w-28"
            direction={sort.direction}
            onSort={() =>
              setSort((current) => nextSortState(current, "updatedAt"))
            }
            sortLabel={sortLabel("updatedAt", t("columns.updatedAt"))}
          >
            {t("columns.updatedAt")}
          </SortableTableHead>
          <TableHead className="w-28 text-right">
            {t("columns.actions")}
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {isPending ? <LoadingTableRows columns={6} /> : null}
        {!isPending && !isError && visibleAttributes.length === 0 ? (
          <TableEmptyState
            columns={6}
            description={
              hasSearch
                ? collection("noResultsDescription")
                : t("emptyDescription")
            }
            title={hasSearch ? collection("noResults") : t("emptyTitle")}
          />
        ) : null}
        {visibleAttributes.map((attribute) => (
          <DataListRow key={attribute.id}>
            <TableCell className="w-[26%] font-medium">
              <div className="flex min-w-0 flex-col gap-1">
                <TruncatedTableText value={attribute.name} />
                <TruncatedTableText
                  className="text-xs text-muted-foreground"
                  value={attribute.comment || common("notSet")}
                />
              </div>
            </TableCell>
            <TableCell className="w-[16%]">
              <TruncatedTableText value={attribute.category} />
            </TableCell>
            <TableCell className="w-[22%]">
              <div className="flex flex-wrap gap-1">
                <Badge variant="outline">
                  {t(`dataTypes.${attribute.dataType}`)}
                </Badge>
                <Badge variant="outline">
                  {t(`sources.${attribute.source}`)}
                </Badge>
                <Badge variant="outline">
                  {t(`valueSources.${attribute.valueSource}`)}
                </Badge>
                <Badge variant="ghost">
                  {t("schemaVersion", {
                    version: attribute.schemaVersion,
                  })}
                </Badge>
              </div>
            </TableCell>
            <TableCell className="w-24">
              <CatalogStatusBadge
                label={common(`status.${attribute.status}`)}
                status={attribute.status}
              />
            </TableCell>
            <TableCell className="w-28">
              {format.dateTime(new Date(attribute.updatedAt), {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </TableCell>
            <TableCell className="w-28">
              <div className="flex shrink-0 justify-end gap-1">
                <IconTooltipButton
                  aria-label={t("actions.edit", { name: attribute.name })}
                  onClick={() => onEdit(attribute)}
                  tooltip={t("actions.edit", { name: attribute.name })}
                  type="button"
                  variant="secondary"
                >
                  <Edit3Icon />
                </IconTooltipButton>
                <IconTooltipButton
                  aria-label={t("actions.deactivate", {
                    name: attribute.name,
                  })}
                  disabled={attribute.status === "inactive"}
                  onClick={() => onDeactivate(attribute)}
                  tooltip={t("actions.deactivate", { name: attribute.name })}
                  type="button"
                  variant="secondary"
                >
                  <PowerIcon />
                </IconTooltipButton>
                <IconTooltipButton
                  aria-label={t("actions.delete", { name: attribute.name })}
                  onClick={() => onDelete(attribute)}
                  tooltip={t("actions.delete", { name: attribute.name })}
                  type="button"
                  variant="secondary"
                >
                  <Trash2Icon />
                </IconTooltipButton>
              </div>
            </TableCell>
          </DataListRow>
        ))}
      </TableBody>
    </DataListTable>
  );
}
