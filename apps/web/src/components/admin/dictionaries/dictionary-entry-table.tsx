"use client";

import { Edit3Icon, PowerIcon, Trash2Icon } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import {
  CatalogStatusBadge,
  LoadingTableRows,
} from "@/components/admin/catalog/catalog-shared";
import { DataListRow, DataListTable } from "@/components/ui/data-list";
import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import { TableEmptyState } from "@/components/ui/table-empty-state";
import {
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TruncatedTableText,
} from "@/components/ui/table";
import type {
  DictionaryEntry,
  DictionaryField,
} from "@/lib/admin-settings/types";
import { formatDictionaryEntryValue } from "@/lib/admin-settings/view-model";

interface DictionaryEntryTableProps {
  entries: DictionaryEntry[];
  fields: DictionaryField[];
  fieldsReady: boolean;
  isError: boolean;
  isPending: boolean;
  onDeactivate: (entry: DictionaryEntry) => void;
  onDelete: (entry: DictionaryEntry) => void;
  onEdit: (entry: DictionaryEntry) => void;
}

export function DictionaryEntryTable({
  entries,
  fields,
  fieldsReady,
  isError,
  isPending,
  onDeactivate,
  onDelete,
  onEdit,
}: DictionaryEntryTableProps) {
  const t = useTranslations("AdminSettings.customDictionaryDetail");
  const common = useTranslations("AdminSettings.common");
  const format = useFormatter();
  const activeFields = fields
    .filter((field) => field.status === "active")
    .slice()
    .sort((first, second) => first.sortOrder - second.sortOrder);
  const valueColumns =
    activeFields.length > 0
      ? activeFields
      : [
          {
            externalId: "__entry",
            id: "__entry",
            label: t("entries.columns.entry"),
          },
        ];
  const columnCount = valueColumns.length + 3;

  return (
    <DataListTable className="min-w-[720px]">
      <TableHeader>
        <TableRow className="border-0 hover:bg-transparent">
          {valueColumns.map((field) => (
            <TableHead key={field.id}>{field.label}</TableHead>
          ))}
          <TableHead>{t("entries.columns.status")}</TableHead>
          <TableHead>{t("entries.columns.updatedAt")}</TableHead>
          <TableHead className="text-right">
            {t("entries.columns.actions")}
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {isPending ? <LoadingTableRows columns={columnCount} /> : null}
        {!isPending && !isError && entries.length === 0 ? (
          <TableEmptyState
            columns={columnCount}
            description={t("entries.emptyDescription")}
            title={t("entries.emptyTitle")}
          />
        ) : null}
        {entries.map((entry) => (
          <DataListRow key={entry.id}>
            {valueColumns.map((field) => (
              <TableCell key={field.id}>
                {field.externalId === "__entry" ? (
                  <EntryFallbackCell entry={entry} />
                ) : (
                  <EntryValueCell
                    value={formatDictionaryEntryValue(
                      entry.values[field.externalId],
                    )}
                  />
                )}
              </TableCell>
            ))}
            <TableCell>
              <CatalogStatusBadge
                label={common(`status.${entry.status}`)}
                status={entry.status}
              />
            </TableCell>
            <TableCell>
              {format.dateTime(new Date(entry.updatedAt), {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </TableCell>
            <TableCell>
              <div className="flex justify-end gap-1">
                <IconTooltipButton
                  aria-label={t("entries.actions.edit", {
                    name: entry.label,
                  })}
                  disabled={!fieldsReady}
                  onClick={() => onEdit(entry)}
                  tooltip={t("entries.actions.edit", {
                    name: entry.label,
                  })}
                  type="button"
                  variant="secondary"
                >
                  <Edit3Icon />
                </IconTooltipButton>
                <IconTooltipButton
                  aria-label={t("entries.actions.deactivate", {
                    name: entry.label,
                  })}
                  disabled={entry.status === "inactive"}
                  onClick={() => onDeactivate(entry)}
                  tooltip={t("entries.actions.deactivate", {
                    name: entry.label,
                  })}
                  type="button"
                  variant="secondary"
                >
                  <PowerIcon />
                </IconTooltipButton>
                <IconTooltipButton
                  aria-label={t("entries.actions.delete", {
                    name: entry.label,
                  })}
                  onClick={() => onDelete(entry)}
                  tooltip={t("entries.actions.delete", {
                    name: entry.label,
                  })}
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

function EntryValueCell({ value }: { value: string }) {
  const common = useTranslations("AdminSettings.common");

  if (!value) {
    return <span className="text-muted-foreground">{common("notSet")}</span>;
  }

  return <TruncatedTableText className="font-medium" value={value} />;
}

function EntryFallbackCell({ entry }: { entry: DictionaryEntry }) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <TruncatedTableText className="font-medium" value={entry.label} />
      <TruncatedTableText
        className="font-mono text-xs text-muted-foreground"
        value={entry.externalId}
      />
    </div>
  );
}
