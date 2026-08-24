"use client";

import { PlusIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import {
  CatalogFormActions,
  CatalogFormSheet,
} from "@/components/admin/catalog/catalog-form-sheet";
import {
  CatalogNotice,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { Button } from "@/components/ui/button";
import type {
  DictionaryField,
  SaveDictionaryFieldInput,
} from "@/lib/admin-settings/types";
import {
  getDictionaryValidationMessages,
  toGeneratedExternalId,
} from "@/lib/admin-settings/view-model";

import { DictionaryFieldRow } from "./dictionary-field-row";
import type {
  DictionaryFieldFormRow,
  FieldRowErrors,
} from "./dictionary-field-row-model";
import {
  buildDictionaryFieldFormRows,
  emptyRow,
  getDuplicateExternalIds,
  getRemovedFieldExternalIds,
  parseJsonFields,
  reindexRows,
  reorderRows,
} from "./dictionary-fields-form-model";

interface DictionaryFieldsFormProps {
  entryTotalCount: number | null;
  error: unknown;
  fields: DictionaryField[];
  isPending: boolean;
  onCancel: () => void;
  onSubmit: (fields: SaveDictionaryFieldInput[]) => void;
}

export function DictionaryFieldsForm({
  entryTotalCount,
  error,
  fields,
  isPending,
  onCancel,
  onSubmit,
}: DictionaryFieldsFormProps) {
  const t = useTranslations("AdminSettings.customDictionaries.fieldsForm");
  const [rows, setRows] = useState<DictionaryFieldFormRow[]>(() => {
    const initialRows = buildDictionaryFieldFormRows(fields);
    return initialRows;
  });
  const [rowErrors, setRowErrors] = useState<Record<string, FieldRowErrors>>(
    {},
  );
  const [schemaDeletionError, setSchemaDeletionError] = useState<string | null>(
    null,
  );
  const [draggedRowId, setDraggedRowId] = useState<string | null>(null);
  const removedFieldExternalIds = getRemovedFieldExternalIds(fields, rows);
  const removingFieldsWithUnknownEntryCount =
    removedFieldExternalIds.length > 0 && entryTotalCount === null;
  const removingFieldsWithEntries =
    removedFieldExternalIds.length > 0 &&
    entryTotalCount !== null &&
    entryTotalCount > 0;
  const hasRowErrors = Object.values(rowErrors).some(
    (errors) => Object.keys(errors).length > 0,
  );
  const saveErrorMessage = error
    ? getCatalogErrorMessage(error, t("errors.saveFailed"))
    : null;
  const visibleFooterError =
    schemaDeletionError ??
    (hasRowErrors ? t("errors.fixFields") : saveErrorMessage);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (removingFieldsWithUnknownEntryCount) {
      setSchemaDeletionError(t("errors.deleteFieldsCountUnknown"));
      return;
    }

    if (removingFieldsWithEntries) {
      setSchemaDeletionError(
        t("errors.deleteFieldsWithEntries", {
          count: entryTotalCount,
        }),
      );
      return;
    }

    setSchemaDeletionError(null);
    const nextErrors: Record<string, FieldRowErrors> = {};
    const nextRows = rows.map((row) => ({
      ...row,
      label: row.label.trim(),
    }));
    const preparedRows = nextRows.map((row, index) => ({
      ...row,
      externalId:
        row.externalId.trim() || toGeneratedExternalId(row.label, "field"),
      sortOrder: index,
    }));
    const duplicateIds = getDuplicateExternalIds(preparedRows);
    const inputs: SaveDictionaryFieldInput[] = [];

    for (const [index, row] of preparedRows.entries()) {
      const errors: FieldRowErrors = {};
      const parsed = parseJsonFields(row, t("errors.jsonObject"));

      if (duplicateIds.includes(row.externalId)) {
        errors.externalId = t("errors.externalIdDuplicate");
      }

      if (!row.label) {
        errors.label = t("errors.labelRequired");
      }

      Object.assign(errors, parsed.errors);

      if (Object.keys(errors).length > 0) {
        nextErrors[row.rowId] = errors;
      } else {
        inputs.push({
          constraints: parsed.constraints,
          dataType: row.dataType,
          externalId: row.externalId,
          format: parsed.format,
          isUnique: row.isUnique,
          label: row.label,
          normalization: parsed.normalization,
          required: row.required,
          sortOrder: index,
          status: row.status,
        });
      }
    }

    setRows(preparedRows);
    setRowErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    onSubmit(inputs.filter((row) => row.externalId || row.label));
  }

  function updateRow(
    rowId: string,
    updater: (row: DictionaryFieldFormRow) => DictionaryFieldFormRow,
  ) {
    setRows((current) =>
      current.map((row) => (row.rowId === rowId ? updater(row) : row)),
    );
    setRowErrors((current) => ({ ...current, [rowId]: {} }));
    setSchemaDeletionError(null);
  }

  function moveRow(rowId: string, direction: -1 | 1) {
    setRows((current) => {
      const currentIndex = current.findIndex((row) => row.rowId === rowId);
      const targetIndex = currentIndex + direction;

      if (
        currentIndex < 0 ||
        targetIndex < 0 ||
        targetIndex >= current.length
      ) {
        return current;
      }

      return reorderRows(current, currentIndex, targetIndex);
    });
  }

  function dropRow(targetRowId: string) {
    setRows((current) => {
      if (!draggedRowId || draggedRowId === targetRowId) {
        return current;
      }

      const currentIndex = current.findIndex(
        (row) => row.rowId === draggedRowId,
      );
      const targetIndex = current.findIndex((row) => row.rowId === targetRowId);

      if (currentIndex < 0 || targetIndex < 0) {
        return current;
      }

      return reorderRows(current, currentIndex, targetIndex);
    });
    setDraggedRowId(null);
  }

  return (
    <CatalogFormSheet
      description={t("description")}
      footer={
        <CatalogFormActions
          cancelLabel={t("cancel")}
          error={visibleFooterError}
          isPending={isPending}
          onCancel={onCancel}
          saveLabel={t("save")}
          savingLabel={t("saving")}
        />
      }
      onSubmit={handleSubmit}
      title={t("title")}
    >
      <div className="flex justify-end">
        <Button
          disabled={isPending}
          onClick={() => {
            setSchemaDeletionError(null);
            setRows((current) => [
              ...current,
              emptyRow({ sortOrder: current.length }),
            ]);
          }}
          size="sm"
          type="button"
          variant="secondary"
        >
          <PlusIcon data-icon="inline-start" />
          {t("add")}
        </Button>
      </div>

      {rows.length === 0 ? (
        <CatalogNotice
          description={t("emptyDescription")}
          title={t("emptyTitle")}
        />
      ) : null}

      {removedFieldExternalIds.length > 0 ? (
        <CatalogNotice
          description={t("deleteWarningDescription", {
            fields: removedFieldExternalIds.join(", "),
          })}
          title={t("deleteWarningTitle")}
          tone={
            removingFieldsWithEntries || removingFieldsWithUnknownEntryCount
              ? "danger"
              : "default"
          }
        />
      ) : null}

      {error ? (
        <CatalogNotice
          description={getDictionaryValidationMessages(error).join("\n")}
          title={getCatalogErrorMessage(error, t("errors.saveFailed"))}
          tone="danger"
        />
      ) : null}

      <div className="flex flex-col gap-5">
        {rows.map((row, index) => (
          <DictionaryFieldRow
            errors={rowErrors[row.rowId] ?? {}}
            index={index}
            isPending={isPending}
            key={row.rowId}
            onDragEnd={() => setDraggedRowId(null)}
            onDragStart={() => setDraggedRowId(row.rowId)}
            onDrop={() => dropRow(row.rowId)}
            onMove={moveRow}
            onRemove={(rowId) => {
              setSchemaDeletionError(null);
              setRows((current) =>
                reindexRows(current.filter((item) => item.rowId !== rowId)),
              );
            }}
            onUpdate={updateRow}
            row={row}
            rowCount={rows.length}
          />
        ))}
      </div>
    </CatalogFormSheet>
  );
}
