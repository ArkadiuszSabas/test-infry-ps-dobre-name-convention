import type {
  CatalogStatus,
  WritableAttributeDataType,
} from "@/lib/admin-settings/types";
import {
  dictionaryFieldTypeOptions,
  getDictionaryFieldTypeOption,
  type DictionaryFieldTypeOption,
} from "@/lib/admin-settings/dictionary-field-presets";
import { parseJsonObject } from "@/lib/admin-settings/dictionary-view-model";

export interface DictionaryFieldFormRow {
  constraintsText: string;
  dataType: WritableAttributeDataType;
  externalId: string;
  formatText: string;
  isUnique: boolean;
  label: string;
  normalizationText: string;
  required: boolean;
  rowId: string;
  sortOrder: number;
  status: CatalogStatus;
}

export interface FieldRowErrors {
  constraints?: string;
  externalId?: string;
  format?: string;
  label?: string;
  normalization?: string;
}

export interface DictionaryFieldRowProps {
  errors: FieldRowErrors;
  index: number;
  isPending: boolean;
  onDragEnd: () => void;
  onDragStart: () => void;
  onDrop: () => void;
  onMove: (rowId: string, direction: -1 | 1) => void;
  onRemove: (rowId: string) => void;
  onUpdate: (
    rowId: string,
    updater: (row: DictionaryFieldFormRow) => DictionaryFieldFormRow,
  ) => void;
  row: DictionaryFieldFormRow;
  rowCount: number;
}

export const statusOptions = ["active", "inactive"] as const;
export const dictionaryFieldFlags = ["required", "unique"] as const;

export function getCurrentTypeOption(
  row: DictionaryFieldFormRow,
): DictionaryFieldTypeOption {
  return getDictionaryFieldTypeOption(
    row.dataType,
    parseOptionalJsonObject(row.formatText),
  );
}

export function getAdvancedSettingCount(row: DictionaryFieldFormRow): number {
  return (
    countJsonKeys(row.constraintsText) +
    countJsonKeys(row.normalizationText) +
    countJsonKeys(row.formatText)
  );
}

export function parseOptionalJsonObject(
  input: string,
): Record<string, unknown> {
  try {
    return parseJsonObject(input);
  } catch {
    return {};
  }
}

export function parseOptionalConstraintsObject(
  input: string,
): Record<string, number | string> {
  const parsed = parseOptionalJsonObject(input);
  const result: Record<string, number | string> = {};

  for (const [key, value] of Object.entries(parsed)) {
    if (typeof value === "number" || typeof value === "string") {
      result[key] = value;
    }
  }

  return result;
}

export function getFlagValues(row: DictionaryFieldFormRow): string[] {
  return [
    row.required ? "required" : null,
    row.isUnique ? "unique" : null,
  ].filter((value): value is string => Boolean(value));
}

export function isCatalogStatus(value: string): value is CatalogStatus {
  return statusOptions.some((status) => status === value);
}

export function isDictionaryFieldTypeOption(
  value: string,
): value is DictionaryFieldTypeOption {
  return dictionaryFieldTypeOptions.some((option) => option === value);
}

function countJsonKeys(value: string): number {
  const normalized = value.trim();

  if (!normalized) {
    return 0;
  }

  try {
    const parsed: unknown = JSON.parse(normalized);

    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return 1;
    }

    return Object.keys(parsed).length;
  } catch {
    return 1;
  }
}
