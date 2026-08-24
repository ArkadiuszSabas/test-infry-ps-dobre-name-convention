import type {
  SystemCatalogDefinition,
  SystemCatalogDisplayMode,
  SystemCatalogExtensionField,
  SystemCatalogOptionParameter,
} from "@/lib/system-catalogs/types";

interface DocumentTypeDisplayExtensionValue {
  displayValue?: string | null;
  extensionFieldId: string;
  textValue?: string | null;
}

export interface DocumentTypeDisplayItem {
  displayLabel?: string;
  displayModeId?: string | null;
  externalId?: string | null;
  extensionValues?: readonly DocumentTypeDisplayExtensionValue[];
  id: string;
  label?: string;
  name?: string;
  parameters?: readonly SystemCatalogOptionParameter[];
}

export interface DocumentTypeDisplayModeOption {
  id: string;
  label: string;
}

export function getActiveDocumentTypeDisplayModes(
  definition: SystemCatalogDefinition | null | undefined,
): SystemCatalogDisplayMode[] {
  return [...(definition?.displayModes ?? [])]
    .filter((mode) => mode.isActive)
    .sort(
      (first, second) =>
        Number(second.isDefault) - Number(first.isDefault) ||
        first.name.localeCompare(second.name) ||
        first.id.localeCompare(second.id),
    );
}

export function getDocumentTypeDisplayModeOptions(
  definition: SystemCatalogDefinition | null | undefined,
): DocumentTypeDisplayModeOption[] {
  return getActiveDocumentTypeDisplayModes(definition).map((mode) => ({
    id: mode.id,
    label: mode.name,
  }));
}

export function shouldShowDocumentTypeDisplayModeSelect(
  definition: SystemCatalogDefinition | null | undefined,
): boolean {
  return getActiveDocumentTypeDisplayModes(definition).length > 1;
}

export function resolveDocumentTypeDisplayModeId({
  definition,
  preferredDisplayModeId,
}: {
  definition: SystemCatalogDefinition | null | undefined;
  preferredDisplayModeId?: string | null;
}): string | null {
  const modes = getActiveDocumentTypeDisplayModes(definition);

  return (
    modes.find((mode) => mode.id === preferredDisplayModeId)?.id ??
    modes.find((mode) => mode.isDefault)?.id ??
    modes[0]?.id ??
    null
  );
}

export function formatDocumentTypeDisplayLabel({
  definition,
  displayModeId,
  documentType,
}: {
  definition?: SystemCatalogDefinition | null;
  displayModeId?: string | null;
  documentType: DocumentTypeDisplayItem;
}): string {
  const effectiveDisplayModeId = resolveDocumentTypeDisplayModeId({
    definition,
    preferredDisplayModeId: displayModeId,
  });
  const mode = getActiveDocumentTypeDisplayModes(definition).find(
    (candidate) => candidate.id === effectiveDisplayModeId,
  );

  if (mode) {
    return formatWithDisplayMode(documentType, mode);
  }

  return formatWithoutDisplayMode(documentType, definition);
}

export function sortDocumentTypeDisplayItems({
  definition,
  displayModeId,
  documentTypes,
}: {
  definition?: SystemCatalogDefinition | null;
  displayModeId?: string | null;
  documentTypes: readonly DocumentTypeDisplayItem[];
}): DocumentTypeDisplayItem[] {
  return [...documentTypes].sort((first, second) => {
    const firstLabel = formatDocumentTypeDisplayLabel({
      definition,
      displayModeId,
      documentType: first,
    });
    const secondLabel = formatDocumentTypeDisplayLabel({
      definition,
      displayModeId,
      documentType: second,
    });

    return (
      firstLabel.localeCompare(secondLabel) || first.id.localeCompare(second.id)
    );
  });
}

function formatWithDisplayMode(
  documentType: DocumentTypeDisplayItem,
  mode: SystemCatalogDisplayMode,
): string {
  const values: string[] = [];

  for (const part of [...mode.parts].sort(
    (first, second) => first.partOrder - second.partOrder,
  )) {
    const value = displayPartValue(documentType, part.extensionFieldId);

    if (!value) {
      continue;
    }

    if (values.length > 0 && part.separatorBefore) {
      values.push(part.separatorBefore);
    }

    values.push(value);
  }

  return (
    normalizeLabel(values.join("")) ?? fallbackDocumentTypeName(documentType)
  );
}

function formatWithoutDisplayMode(
  documentType: DocumentTypeDisplayItem,
  definition: SystemCatalogDefinition | null | undefined,
): string {
  if (!definition) {
    return fallbackDocumentTypeLabel(documentType);
  }

  return fallbackDocumentTypeName(documentType);
}

function displayPartValue(
  documentType: DocumentTypeDisplayItem,
  extensionFieldId: string | null,
): string | null {
  if (!extensionFieldId) {
    return normalizeLabel(documentType.name ?? documentType.label);
  }

  return extensionFieldValue(documentType, { id: extensionFieldId });
}

function extensionFieldValue(
  documentType: DocumentTypeDisplayItem,
  field: Pick<SystemCatalogExtensionField, "id"> &
    Partial<Pick<SystemCatalogExtensionField, "code">>,
): string | null {
  const extensionValue = documentType.extensionValues?.find(
    (value) => value.extensionFieldId === field.id,
  );

  return (
    normalizeLabel(extensionValue?.displayValue) ??
    normalizeLabel(extensionValue?.textValue) ??
    normalizeLabel(
      field.code
        ? documentType.parameters?.find(
            (parameter) => parameter.code === field.code,
          )?.value
        : null,
    )
  );
}

function fallbackDocumentTypeLabel(documentType: DocumentTypeDisplayItem) {
  return (
    normalizeLabel(documentType.displayLabel) ??
    normalizeLabel(documentType.label) ??
    normalizeLabel(documentType.name) ??
    documentType.id
  );
}

function fallbackDocumentTypeName(documentType: DocumentTypeDisplayItem) {
  return (
    normalizeLabel(documentType.name) ?? fallbackDocumentTypeLabel(documentType)
  );
}

function normalizeLabel(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}
