import type { DictionaryField } from "@/lib/admin-settings/types";
import {
  buildDictionaryFieldDraftRows,
  formatJsonObject,
  parseJsonObject,
} from "@/lib/admin-settings/view-model";

import type {
  DictionaryFieldFormRow,
  FieldRowErrors,
} from "./dictionary-field-row-model";

export function buildDictionaryFieldFormRows(
  fields: readonly DictionaryField[],
): DictionaryFieldFormRow[] {
  return buildDictionaryFieldDraftRows(fields).map((field) => ({
    constraintsText: formatJsonObject(field.constraints),
    dataType: field.dataType,
    externalId: field.externalId,
    formatText: formatJsonObject(field.format),
    isUnique: field.isUnique,
    label: field.label,
    normalizationText: formatJsonObject(field.normalization),
    required: field.required,
    rowId: field.rowId,
    sortOrder: field.sortOrder,
    status: field.status,
  }));
}

export function emptyRow(
  overrides: Partial<DictionaryFieldFormRow> = {},
): DictionaryFieldFormRow {
  return {
    constraintsText: "",
    dataType: "string",
    externalId: "",
    formatText: "",
    isUnique: false,
    label: "",
    normalizationText: "",
    required: false,
    rowId: `new-${crypto.randomUUID()}`,
    sortOrder: 0,
    status: "active",
    ...overrides,
  };
}

export function parseJsonFields(
  row: DictionaryFieldFormRow,
  errorMessage: string,
): {
  constraints: Record<string, number | string>;
  errors: FieldRowErrors;
  format: Record<string, unknown>;
  normalization: Record<string, unknown>;
} {
  const errors: FieldRowErrors = {};
  let constraints: Record<string, number | string> = {};
  let format: Record<string, unknown> = {};
  let normalization: Record<string, unknown> = {};

  try {
    constraints = parseConstraintsObject(row.constraintsText);
  } catch {
    errors.constraints = errorMessage;
  }

  try {
    normalization = parseJsonObject(row.normalizationText);
  } catch {
    errors.normalization = errorMessage;
  }

  try {
    format = parseJsonObject(row.formatText);
  } catch {
    errors.format = errorMessage;
  }

  return { constraints, errors, format, normalization };
}

export function getDuplicateExternalIds(
  rows: readonly DictionaryFieldFormRow[],
): string[] {
  const seen = new Set<string>();
  const duplicates = new Set<string>();

  for (const row of rows) {
    const normalized = row.externalId.trim();

    if (!normalized) {
      continue;
    }

    if (seen.has(normalized)) {
      duplicates.add(normalized);
    }

    seen.add(normalized);
  }

  return [...duplicates].sort();
}

export function getRemovedFieldExternalIds(
  fields: readonly DictionaryField[],
  rows: readonly DictionaryFieldFormRow[],
): string[] {
  const rowExternalIds = new Set(
    rows.map((row) => row.externalId.trim()).filter(Boolean),
  );
  return fields
    .map((field) => field.externalId)
    .filter((externalId) => !rowExternalIds.has(externalId))
    .sort();
}

export function reorderRows(
  rows: readonly DictionaryFieldFormRow[],
  fromIndex: number,
  toIndex: number,
): DictionaryFieldFormRow[] {
  const nextRows = [...rows];
  const [movedRow] = nextRows.splice(fromIndex, 1);

  if (!movedRow) {
    return nextRows;
  }

  nextRows.splice(toIndex, 0, movedRow);
  return reindexRows(nextRows);
}

export function reindexRows(
  rows: readonly DictionaryFieldFormRow[],
): DictionaryFieldFormRow[] {
  return rows.map((row, index) => ({ ...row, sortOrder: index }));
}

function parseConstraintsObject(
  input: string,
): Record<string, number | string> {
  const parsed = parseJsonObject(input);
  const result: Record<string, number | string> = {};

  for (const [key, value] of Object.entries(parsed)) {
    if (typeof value !== "number" && typeof value !== "string") {
      throw new Error("Dictionary field constraints must be strings/numbers.");
    }

    result[key] = value;
  }

  return result;
}
