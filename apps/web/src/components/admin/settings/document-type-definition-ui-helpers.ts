import type { SystemCatalogDisplayPartSourceType } from "@/lib/system-catalogs/types";
import type {
  DocumentTypeDefinition,
  SystemCatalogExtensionField,
} from "@/lib/admin-settings/types";
import type {
  SystemCatalogDefinitionDraft,
  SystemCatalogDisplayModePartDraft,
} from "@/lib/admin-settings/view-model";

export const NONE_VALUE = "__none";

type DefinitionErrorKey =
  | "errors.defaultModeRequired"
  | "errors.definitionRequired"
  | "errors.dictionaryRequired"
  | "errors.duplicateFieldCode"
  | "errors.duplicateModeName"
  | "errors.fieldIdentityRequired"
  | "errors.modeFieldRequired"
  | "errors.modeNameRequired"
  | "errors.modePartsRequired";

type DefinitionTranslator = (key: DefinitionErrorKey) => string;

export interface RequiredFieldBackfillBlock {
  documentTypes: DocumentTypeDefinition[];
  fieldLabel: string;
  fieldRowId: string;
  isNewField: boolean;
}

export function createModePart(
  sourceType: SystemCatalogDisplayPartSourceType,
): SystemCatalogDisplayModePartDraft {
  return {
    extensionFieldRowId: null,
    rowId: createDraftId("part"),
    separatorBefore: sourceType === "extension_field" ? " - " : "",
    sourceType,
  };
}

export function moveField(
  draft: SystemCatalogDefinitionDraft,
  index: number,
  direction: -1 | 1,
): SystemCatalogDefinitionDraft {
  return {
    ...draft,
    fields: moveArrayItem(draft.fields, index, direction),
  };
}

export function moveMode(
  draft: SystemCatalogDefinitionDraft,
  index: number,
  direction: -1 | 1,
): SystemCatalogDefinitionDraft {
  return {
    ...draft,
    displayModes: moveArrayItem(draft.displayModes, index, direction),
  };
}

export function clearDisplayModeFieldReferences(
  draft: SystemCatalogDefinitionDraft,
  fieldRowId: string,
): SystemCatalogDefinitionDraft {
  return {
    ...draft,
    displayModes: draft.displayModes.map((mode) => ({
      ...mode,
      parts: mode.parts.map((part) =>
        part.extensionFieldRowId === fieldRowId
          ? { ...part, extensionFieldRowId: null }
          : part,
      ),
    })),
  };
}

export function moveArrayItem<T>(
  items: readonly T[],
  index: number,
  direction: -1 | 1,
): T[] {
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= items.length) {
    return [...items];
  }

  const next = [...items];
  const [item] = next.splice(index, 1);
  if (item) {
    next.splice(targetIndex, 0, item);
  }
  return next;
}

export function getDefinitionDraftError(
  draft: SystemCatalogDefinitionDraft,
  t: DefinitionTranslator,
): string | null {
  const codes = new Set<string>();

  for (const field of draft.fields) {
    const code = field.code.trim();
    if (!field.label.trim() || !code) {
      return t("errors.fieldIdentityRequired");
    }

    if (codes.has(code)) {
      return t("errors.duplicateFieldCode");
    }
    codes.add(code);

    if (field.valueType === "dictionary" && !field.dictionaryId) {
      return t("errors.dictionaryRequired");
    }
  }

  const activeModes = draft.displayModes.filter((mode) => mode.isActive);
  const defaultModes = activeModes.filter((mode) => mode.isDefault);

  if (activeModes.length > 0 && defaultModes.length !== 1) {
    return t("errors.defaultModeRequired");
  }

  const activeFieldRowIds = new Set(
    draft.fields.filter((field) => field.isActive).map((field) => field.rowId),
  );
  const modeNames = new Set<string>();

  for (const mode of draft.displayModes) {
    const modeName = mode.name.trim();
    if (!modeName) {
      return t("errors.modeNameRequired");
    }

    const normalizedModeName = modeName.toLowerCase();
    if (modeNames.has(normalizedModeName)) {
      return t("errors.duplicateModeName");
    }
    modeNames.add(normalizedModeName);

    if (mode.isActive && mode.parts.length === 0) {
      return t("errors.modePartsRequired");
    }

    for (const part of mode.parts) {
      if (
        part.sourceType === "extension_field" &&
        (!part.extensionFieldRowId ||
          !activeFieldRowIds.has(part.extensionFieldRowId))
      ) {
        return t("errors.modeFieldRequired");
      }
    }
  }

  return null;
}

export function getRequiredFieldBackfillBlocks({
  documentTypes,
  draft,
  existingFields,
}: {
  documentTypes: readonly DocumentTypeDefinition[];
  draft: SystemCatalogDefinitionDraft;
  existingFields: readonly SystemCatalogExtensionField[];
}): RequiredFieldBackfillBlock[] {
  const existingFieldsById = new Map(
    existingFields.map((field) => [field.id, field]),
  );
  const activeDocumentTypes = [...documentTypes]
    .filter((documentType) => documentType.status === "active")
    .sort((first, second) =>
      first.displayLabel.localeCompare(second.displayLabel),
    );

  if (activeDocumentTypes.length === 0) {
    return [];
  }

  return draft.fields.flatMap((field): RequiredFieldBackfillBlock[] => {
    const existingField = field.id
      ? existingFieldsById.get(field.id)
      : undefined;
    const becameRequired =
      field.isActive &&
      field.isRequired &&
      (!existingField || !existingField.isActive || !existingField.isRequired);

    if (!becameRequired) {
      return [];
    }

    const missingDocumentTypes = activeDocumentTypes.filter(
      (documentType) => !hasDocumentTypeExtensionValue(documentType, field),
    );

    if (missingDocumentTypes.length === 0) {
      return [];
    }

    return [
      {
        documentTypes: missingDocumentTypes,
        fieldLabel:
          field.label.trim() || field.code.trim() || "New extension field",
        fieldRowId: field.rowId,
        isNewField: !field.id,
      },
    ];
  });
}

let draftIdSeed = 0;

export function createDraftId(prefix: string): string {
  draftIdSeed += 1;
  return `${prefix}-${Date.now()}-${draftIdSeed}`;
}

function hasDocumentTypeExtensionValue(
  documentType: DocumentTypeDefinition,
  field: { id?: string; valueType: "dictionary" | "text" },
): boolean {
  if (!field.id) {
    return false;
  }

  const value = documentType.extensionValues.find(
    (candidate) => candidate.extensionFieldId === field.id,
  );

  if (!value) {
    return false;
  }

  return field.valueType === "dictionary"
    ? Boolean(value.dictionaryEntryId?.trim())
    : Boolean(value.textValue?.trim());
}
