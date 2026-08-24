import { isApiError } from "@/lib/api/errors";
import type { DocumentTypeDisplayItem } from "@/lib/system-catalogs/document-type-display";

import type {
  DictionaryLookupEntry,
  DocumentMetadataSchemaField,
  ManualUploadDocumentType,
  ManualUploadMetadataField,
  MetadataDataType,
  MetadataScalar,
  DocumentStatus,
  OcrPipelineRunStatus,
} from "./types";

export type InboxPreviewState =
  | { kind: "available"; url: string }
  | { kind: "unavailable" };

export type DocumentParameterControlKind =
  | "checkbox"
  | "date"
  | "datetime"
  | "number"
  | "select"
  | "text"
  | "unsupported";

export type DocumentParameterTypeKind =
  | "boolean"
  | "date"
  | "datetime"
  | "integer"
  | "legacy_scalar"
  | "number"
  | "string"
  | "unsupported"
  | "uuid";

export interface DocumentParameterOption {
  label: string;
  value: string;
}

export interface DocumentParameterItem {
  controlKind: DocumentParameterControlKind;
  field: DocumentMetadataSchemaField;
  inputValue: string;
  missing: boolean;
  options: DocumentParameterOption[];
  requirement: "optional" | "required";
  selectedOptionLabel: string | null;
  typeKind: DocumentParameterTypeKind;
  value: MetadataScalar | undefined;
}

export interface DocumentParameterSection {
  items: DocumentParameterItem[];
  requirement: "optional" | "required";
}

export interface BuildDocumentParameterSectionsInput {
  dictionaryOptionsById?: ReadonlyMap<string, readonly DictionaryLookupEntry[]>;
  fields: readonly DocumentMetadataSchemaField[];
  values: Record<string, MetadataScalar>;
}

export interface InboxDocumentTypeFilterOption {
  id: string;
  name: string;
}

export function formatFileSize(
  bytes: number | null,
  formatNumber: (
    value: number,
    options?: { maximumFractionDigits?: number },
  ) => string,
  unknownLabel = "Unknown",
): string {
  if (bytes === null) {
    return unknownLabel;
  }

  if (bytes < 1024) {
    return `${formatNumber(bytes, { maximumFractionDigits: 0 })} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${formatNumber(bytes / 1024, { maximumFractionDigits: 1 })} KB`;
  }

  return `${formatNumber(bytes / (1024 * 1024), { maximumFractionDigits: 1 })} MB`;
}

export function getDocumentTypeFilterOptions({
  documentTypeFilters,
  documentTypes,
}: {
  documentTypeFilters: readonly InboxDocumentTypeFilterOption[];
  documentTypes: readonly DocumentTypeDisplayItem[];
}): DocumentTypeDisplayItem[] {
  const documentTypesById = new Map(
    documentTypes.map((documentType) => [documentType.id, documentType]),
  );

  return documentTypeFilters.map(
    (filter) =>
      documentTypesById.get(filter.id) ?? {
        id: filter.id,
        label: filter.name,
        parameters: [],
      },
  );
}

export function getUploadDocumentTypeOptions({
  manualUploadDocumentTypes,
  systemCatalogOptions,
}: {
  manualUploadDocumentTypes: readonly ManualUploadDocumentType[];
  systemCatalogOptions: readonly DocumentTypeDisplayItem[];
}): readonly DocumentTypeDisplayItem[] {
  const systemCatalogOptionsById = new Map(
    systemCatalogOptions.map((option) => [option.id, option]),
  );

  return manualUploadDocumentTypes.map(
    (documentType) =>
      systemCatalogOptionsById.get(documentType.id) ?? {
        externalId: documentType.externalId,
        id: documentType.id,
        label: documentType.name,
        name: documentType.name,
        parameters: [],
      },
  );
}

export function getActiveDocumentTypeId({
  options,
  selectedDocumentTypeId,
}: {
  options: readonly DocumentTypeDisplayItem[];
  selectedDocumentTypeId: string;
}): string {
  return (
    options.find((option) => option.id === selectedDocumentTypeId)?.id ??
    options[0]?.id ??
    ""
  );
}

export function getInboxErrorMessage(
  error: unknown,
  fallbackMessage: string,
): string {
  if (isApiError(error)) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallbackMessage;
}

export function getManualUploadDictionaryIds(
  fields: readonly Pick<ManualUploadMetadataField, "dictionaryId">[],
): string[] {
  return Array.from(
    new Set(
      fields
        .map((field) => field.dictionaryId)
        .filter((dictionaryId): dictionaryId is string =>
          Boolean(dictionaryId),
        ),
    ),
  );
}

export function buildDocumentParameterSections({
  dictionaryOptionsById = new Map(),
  fields,
  values,
}: BuildDocumentParameterSectionsInput): DocumentParameterSection[] {
  const items = fields.map((field) =>
    toDocumentParameterItem({
      dictionaryEntries:
        field.dictionaryId !== null
          ? (dictionaryOptionsById.get(field.dictionaryId) ?? [])
          : [],
      field,
      value: values[field.key],
    }),
  );
  const requiredItems = items.filter((item) => item.requirement === "required");
  const optionalItems = items.filter((item) => item.requirement === "optional");
  const sections: DocumentParameterSection[] = [];

  if (requiredItems.length > 0) {
    sections.push({ items: requiredItems, requirement: "required" });
  }

  if (optionalItems.length > 0) {
    sections.push({ items: optionalItems, requirement: "optional" });
  }

  return sections;
}

export function getInboxPreviewState(
  previewUrl: string | null | undefined,
): InboxPreviewState {
  if (previewUrl) {
    return { kind: "available", url: previewUrl };
  }

  return { kind: "unavailable" };
}

export function getInboxDocumentStatus(
  documentStatus: DocumentStatus,
  latestOcrRunStatus: OcrPipelineRunStatus | undefined,
): DocumentStatus {
  return latestOcrRunStatus === "failed" ? "failed" : documentStatus;
}

function toDocumentParameterItem({
  dictionaryEntries,
  field,
  value,
}: {
  dictionaryEntries: readonly DictionaryLookupEntry[];
  field: DocumentMetadataSchemaField;
  value: MetadataScalar | undefined;
}): DocumentParameterItem {
  const missing = isMetadataValueMissing(value);
  const options = parameterOptions(field, dictionaryEntries, value);
  const inputValue = formatParameterInputValue(value, field.dataType);

  return {
    controlKind: parameterControlKind(field),
    field,
    inputValue,
    missing,
    options,
    requirement: field.required ? "required" : "optional",
    selectedOptionLabel:
      typeof value === "string"
        ? (options.find((option) => option.value === value)?.label ?? null)
        : null,
    typeKind: parameterTypeKind(field),
    value,
  };
}

function parameterControlKind(
  field: DocumentMetadataSchemaField,
): DocumentParameterControlKind {
  if (
    field.valueSource === "dictionary" ||
    field.valueSource === "inline_allowed_values" ||
    field.allowedValues.length > 0
  ) {
    return "select";
  }

  switch (field.dataType) {
    case "boolean":
      return "checkbox";
    case "date":
      return "date";
    case "datetime":
      return "datetime";
    case "integer":
    case "number":
      return "number";
    case "legacy_scalar":
    case "string":
      return "text";
    default:
      return "unsupported";
  }
}

function parameterTypeKind(
  field: DocumentMetadataSchemaField,
): DocumentParameterTypeKind {
  if (field.dataType === "string" && hasUuidPattern(field.constraints)) {
    return "uuid";
  }

  if (isKnownDataType(field.dataType)) {
    return field.dataType;
  }

  return "unsupported";
}

function parameterOptions(
  field: DocumentMetadataSchemaField,
  dictionaryEntries: readonly DictionaryLookupEntry[],
  value: MetadataScalar | undefined,
): DocumentParameterOption[] {
  const options =
    field.valueSource === "dictionary"
      ? dictionaryEntries
          .slice()
          .sort(dictionaryEntrySort)
          .map((entry) => ({
            label: entry.label,
            value: entry.externalId,
          }))
      : field.allowedValues.map((allowedValue) => ({
          label: allowedValue,
          value: allowedValue,
        }));

  if (
    typeof value !== "string" ||
    !value ||
    options.some((option) => option.value === value)
  ) {
    return options;
  }

  return [{ label: value, value }, ...options];
}

function dictionaryEntrySort(
  first: DictionaryLookupEntry,
  second: DictionaryLookupEntry,
): number {
  const firstSortOrder = first.sortOrder ?? Number.MAX_SAFE_INTEGER;
  const secondSortOrder = second.sortOrder ?? Number.MAX_SAFE_INTEGER;
  return (
    firstSortOrder - secondSortOrder ||
    first.label.localeCompare(second.label) ||
    first.externalId.localeCompare(second.externalId)
  );
}

function formatParameterInputValue(
  value: MetadataScalar | undefined,
  dataType: MetadataDataType,
): string {
  if (isMetadataValueMissing(value)) {
    return "";
  }

  if (dataType === "datetime" && typeof value === "string") {
    return toDateTimeLocalInputValue(value);
  }

  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }

  return String(value);
}

function toDateTimeLocalInputValue(value: string): string {
  const match = value.match(
    /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?$/u,
  );
  return match?.[1] ?? value;
}

function isMetadataValueMissing(value: MetadataScalar | undefined): boolean {
  return value === undefined || value === null || value === "";
}

function isKnownDataType(
  dataType: MetadataDataType,
): dataType is Exclude<DocumentParameterTypeKind, "unsupported" | "uuid"> {
  return (
    dataType === "boolean" ||
    dataType === "date" ||
    dataType === "datetime" ||
    dataType === "integer" ||
    dataType === "legacy_scalar" ||
    dataType === "number" ||
    dataType === "string"
  );
}

function hasUuidPattern(constraints: Record<string, number | string>): boolean {
  const pattern = constraints.pattern;
  return (
    typeof pattern === "string" &&
    pattern.includes("{8}") &&
    pattern.includes("{12}") &&
    pattern.toLowerCase().includes("a-f")
  );
}
