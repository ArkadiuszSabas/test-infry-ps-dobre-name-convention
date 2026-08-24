import type {
  DocumentTypeDefinition,
  DocumentTypeExtensionValueInput,
  SaveSystemCatalogDefinitionInput,
  SystemCatalogDefinition,
  SystemCatalogDisplayPartSourceType,
  SystemCatalogExtensionField,
  SystemCatalogExtensionValueType,
  SystemCatalogOption,
} from "./types";

export interface SystemCatalogFieldDraft {
  rowId: string;
  id?: string;
  code: string;
  label: string;
  valueType: SystemCatalogExtensionValueType;
  dictionaryId: string | null;
  mappedAttributeDefinitionId: string | null;
  isRequired: boolean;
  showInOverview: boolean;
  isActive: boolean;
}

export interface SystemCatalogDisplayModePartDraft {
  rowId: string;
  id?: string;
  sourceType: SystemCatalogDisplayPartSourceType;
  extensionFieldRowId: string | null;
  separatorBefore: string;
}

export interface SystemCatalogDisplayModeDraft {
  rowId: string;
  id?: string;
  name: string;
  isDefault: boolean;
  isActive: boolean;
  parts: SystemCatalogDisplayModePartDraft[];
}

export interface SystemCatalogDefinitionDraft {
  fields: SystemCatalogFieldDraft[];
  displayModes: SystemCatalogDisplayModeDraft[];
}

export interface DocumentTypeParameterFilter {
  code: string;
  label: string;
  options: DocumentTypeParameterFilterOption[];
}

export interface DocumentTypeParameterFilterOption {
  count: number;
  value: string;
}

export type DocumentTypeExtensionDraftValues = Record<string, string>;

export function buildSystemCatalogDefinitionDraft(
  definition: SystemCatalogDefinition,
): SystemCatalogDefinitionDraft {
  const fields = [...definition.fields]
    .sort(systemCatalogFieldSort)
    .map((field) => ({
      code: field.code,
      dictionaryId: field.dictionaryId,
      id: field.id,
      isActive: field.isActive,
      isRequired: field.isRequired,
      label: field.label,
      mappedAttributeDefinitionId: field.mappedAttributeDefinitionId,
      rowId: field.id,
      showInOverview: field.showInOverview,
      valueType: field.valueType,
    }));
  const fieldRowIdsById = new Map(
    fields.map((field) => [field.id, field.rowId]),
  );

  return {
    displayModes: definition.displayModes.map((mode) => ({
      id: mode.id,
      isActive: mode.isActive,
      isDefault: mode.isDefault,
      name: mode.name,
      parts: [...mode.parts].sort(displayModePartSort).map((part) => ({
        extensionFieldRowId: part.extensionFieldId
          ? (fieldRowIdsById.get(part.extensionFieldId) ?? null)
          : null,
        id: part.id,
        rowId: part.id,
        separatorBefore: part.separatorBefore ?? "",
        sourceType: part.sourceType,
      })),
      rowId: mode.id,
    })),
    fields,
  };
}

export function toSaveSystemCatalogDefinitionInput(
  draft: SystemCatalogDefinitionDraft,
): SaveSystemCatalogDefinitionInput {
  return {
    displayModes: draft.displayModes.map((mode) => ({
      ...(mode.id ? { id: mode.id } : {}),
      isActive: mode.isActive,
      isDefault: mode.isDefault,
      name: mode.name.trim(),
      parts: mode.parts.map((part, partIndex) => {
        const field = draft.fields.find(
          (candidate) => candidate.rowId === part.extensionFieldRowId,
        );
        const separatorBefore = normalizeOptionalSeparator(
          part.separatorBefore,
        );

        return {
          ...(part.id ? { id: part.id } : {}),
          ...(part.sourceType === "extension_field" && field?.id
            ? { extensionFieldId: field.id }
            : {}),
          ...(part.sourceType === "extension_field" && field && !field.id
            ? { extensionFieldCode: field.code.trim() }
            : {}),
          ...(separatorBefore ? { separatorBefore } : {}),
          partOrder: partIndex,
          sourceType: part.sourceType,
        };
      }),
    })),
    fields: draft.fields.map((field, fieldIndex) => ({
      ...(field.id ? { id: field.id } : {}),
      code: field.code.trim(),
      dictionaryId:
        field.valueType === "dictionary" ? field.dictionaryId : null,
      fieldOrder: fieldIndex,
      isActive: field.isActive,
      isRequired: field.isRequired,
      label: field.label.trim(),
      mappedAttributeDefinitionId: field.mappedAttributeDefinitionId,
      showInOverview: field.showInOverview,
      valueType: field.valueType,
    })),
  };
}

export function getActiveSystemCatalogFields(
  fields: readonly SystemCatalogExtensionField[],
): SystemCatalogExtensionField[] {
  return fields.filter((field) => field.isActive).sort(systemCatalogFieldSort);
}

export function getSystemCatalogExtensionDictionaryIds(
  fields: readonly SystemCatalogExtensionField[],
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

export function buildDocumentTypeExtensionDraftValues(
  documentType: DocumentTypeDefinition | null,
): DocumentTypeExtensionDraftValues {
  const values: DocumentTypeExtensionDraftValues = {};

  for (const value of documentType?.extensionValues ?? []) {
    if (value.valueType === "dictionary" && value.dictionaryEntryId) {
      values[value.extensionFieldId] = value.dictionaryEntryId;
    }

    if (value.valueType === "text" && value.textValue) {
      values[value.extensionFieldId] = value.textValue;
    }
  }

  return values;
}

export function getMissingRequiredDocumentTypeExtensionFieldIds(
  fields: readonly SystemCatalogExtensionField[],
  values: DocumentTypeExtensionDraftValues,
): string[] {
  return getActiveSystemCatalogFields(fields)
    .filter((field) => field.isRequired && !values[field.id]?.trim())
    .map((field) => field.id);
}

export function hasDocumentTypeExtensionDraftChanges(
  fields: readonly SystemCatalogExtensionField[],
  initialValues: DocumentTypeExtensionDraftValues,
  currentValues: DocumentTypeExtensionDraftValues,
): boolean {
  return getActiveSystemCatalogFields(fields).some(
    (field) =>
      normalizeDraftValue(initialValues[field.id]) !==
      normalizeDraftValue(currentValues[field.id]),
  );
}

export function toDocumentTypeExtensionValueInput(
  fields: readonly SystemCatalogExtensionField[],
  values: DocumentTypeExtensionDraftValues,
): DocumentTypeExtensionValueInput[] {
  return getActiveSystemCatalogFields(fields).flatMap(
    (field): DocumentTypeExtensionValueInput[] => {
      const rawValue = values[field.id]?.trim() ?? "";

      if (!rawValue) {
        return [];
      }

      if (field.valueType === "dictionary") {
        return [
          {
            dictionaryEntryId: rawValue,
            extensionFieldId: field.id,
          },
        ];
      }

      return [
        {
          extensionFieldId: field.id,
          textValue: rawValue,
        },
      ];
    },
  );
}

export function sortSystemCatalogOptions(
  options: readonly SystemCatalogOption[],
): SystemCatalogOption[] {
  return [...options].sort((first, second) => {
    const labelComparison = first.label.localeCompare(second.label);
    return labelComparison === 0
      ? first.id.localeCompare(second.id)
      : labelComparison;
  });
}

export function getDocumentTypeParameterFilters(
  documentTypes: readonly DocumentTypeDefinition[],
): DocumentTypeParameterFilter[] {
  const filters = new Map<
    string,
    {
      label: string;
      values: Map<string, number>;
    }
  >();

  for (const documentType of documentTypes) {
    for (const parameter of documentType.parameters) {
      const value = parameter.value?.trim();

      if (!value) {
        continue;
      }

      const existing = filters.get(parameter.code) ?? {
        label: parameter.label,
        values: new Map<string, number>(),
      };

      existing.values.set(value, (existing.values.get(value) ?? 0) + 1);
      filters.set(parameter.code, existing);
    }
  }

  return [...filters.entries()]
    .map(([code, filter]) => ({
      code,
      label: filter.label,
      options: [...filter.values.entries()]
        .map(([value, count]) => ({ count, value }))
        .sort(
          (first, second) =>
            first.value.localeCompare(second.value) ||
            first.count - second.count,
        ),
    }))
    .sort((first, second) => first.label.localeCompare(second.label));
}

export function normalizeDocumentTypeParameterFilterValues(
  parameterFilters: readonly DocumentTypeParameterFilter[],
  values: Readonly<Record<string, string | null | undefined>>,
): Record<string, string | null> {
  return Object.fromEntries(
    parameterFilters.map((filter) => {
      const selectedValue = values[filter.code] ?? null;
      const hasSelectedValue = filter.options.some(
        (option) => option.value === selectedValue,
      );

      return [filter.code, hasSelectedValue ? selectedValue : null];
    }),
  );
}

export function hasActiveDocumentTypeParameterFilters(
  values: Readonly<Record<string, string | null | undefined>>,
): boolean {
  return Object.values(values).some(Boolean);
}

export function filterDocumentTypesByParameterFilters(
  documentTypes: readonly DocumentTypeDefinition[],
  activeFilters: Readonly<Record<string, string | null | undefined>>,
): DocumentTypeDefinition[] {
  const filterEntries = Object.entries(activeFilters).filter(([, value]) =>
    Boolean(value),
  );

  if (filterEntries.length === 0) {
    return [...documentTypes];
  }

  return documentTypes.filter((documentType) =>
    filterEntries.every(([code, value]) =>
      documentType.parameters.some(
        (parameter) =>
          parameter.code === code && parameter.value?.trim() === value,
      ),
    ),
  );
}

function systemCatalogFieldSort(
  first: SystemCatalogExtensionField,
  second: SystemCatalogExtensionField,
): number {
  const orderComparison = first.fieldOrder - second.fieldOrder;
  return orderComparison === 0
    ? first.label.localeCompare(second.label)
    : orderComparison;
}

function displayModePartSort(
  first: { partOrder: number },
  second: { partOrder: number },
): number {
  return first.partOrder - second.partOrder;
}

function normalizeOptionalSeparator(value: string): string | null {
  return value.length > 0 ? value : null;
}

function normalizeDraftValue(value: string | undefined): string {
  return value?.trim() ?? "";
}
