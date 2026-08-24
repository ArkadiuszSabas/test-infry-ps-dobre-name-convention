import assert from "node:assert/strict";
import test from "node:test";

import type {
  DocumentTypeDefinition,
  SystemCatalogExtensionField,
} from "@/lib/admin-settings/types";
import type { SystemCatalogDefinitionDraft } from "@/lib/admin-settings/view-model";

import {
  clearDisplayModeFieldReferences,
  getDefinitionDraftError,
  getRequiredFieldBackfillBlocks,
} from "./document-type-definition-ui-helpers";

test("definition draft validation rejects inactive extension field parts", () => {
  const draft = definitionDraft();
  draft.fields[0] = { ...draft.fields[0], isActive: false };

  assert.equal(
    getDefinitionDraftError(draft, (key) => key),
    "errors.modeFieldRequired",
  );
});

test("definition draft validation rejects invalid inactive display modes", () => {
  const draft = definitionDraft();
  draft.fields[0] = { ...draft.fields[0], isActive: false };
  draft.displayModes[0] = { ...draft.displayModes[0], isActive: false };

  assert.equal(
    getDefinitionDraftError(draft, (key) => key),
    "errors.modeFieldRequired",
  );
});

test("definition draft validation rejects inactive dictionary fields without dictionary", () => {
  const draft = definitionDraft();
  draft.fields[0] = {
    ...draft.fields[0],
    dictionaryId: null,
    isActive: false,
  };
  draft.displayModes[0] = {
    ...draft.displayModes[0],
    isActive: false,
    parts: [draft.displayModes[0]!.parts[0]!],
  };

  assert.equal(
    getDefinitionDraftError(draft, (key) => key),
    "errors.dictionaryRequired",
  );
});

test("definition draft validation rejects duplicate display mode names", () => {
  const draft = definitionDraft();
  draft.displayModes.push({
    ...draft.displayModes[0]!,
    isDefault: false,
    name: " typ - pion ",
    rowId: "mode-duplicate",
  });

  assert.equal(
    getDefinitionDraftError(draft, (key) => key),
    "errors.duplicateModeName",
  );
});

test("definition draft validation allows inactive display modes without parts", () => {
  const draft = definitionDraft();
  draft.displayModes[0] = {
    ...draft.displayModes[0]!,
    isActive: false,
    parts: [],
  };

  assert.equal(
    getDefinitionDraftError(draft, (key) => key),
    null,
  );
});

test("clearing display mode field references resets dependent parts", () => {
  const draft = clearDisplayModeFieldReferences(
    definitionDraft(),
    "field-pion",
  );

  assert.equal(draft.displayModes[0]?.parts[1]?.extensionFieldRowId, null);
  assert.equal(
    getDefinitionDraftError(draft, (key) => key),
    "errors.modeFieldRequired",
  );
});

test("required field backfill validation lists active document types missing existing field values", () => {
  const draft = definitionDraft();
  draft.fields[0] = {
    ...draft.fields[0]!,
    id: "field-pion-id",
    isRequired: true,
  };

  const blocks = getRequiredFieldBackfillBlocks({
    documentTypes: [
      documentTypeFixture({
        displayLabel: "Typ 2",
        id: "type-2",
        values: [],
      }),
      documentTypeFixture({
        displayLabel: "Typ 1",
        id: "type-1",
        values: [
          {
            dictionaryEntryId: "entry-pion",
            extensionFieldId: "field-pion-id",
          },
        ],
      }),
      documentTypeFixture({
        displayLabel: "Typ inactive",
        id: "type-inactive",
        status: "inactive",
        values: [],
      }),
    ],
    draft,
    existingFields: [
      systemCatalogFieldFixture({
        id: "field-pion-id",
        isRequired: false,
      }),
    ],
  });

  assert.equal(blocks.length, 1);
  assert.equal(blocks[0]?.fieldLabel, "Pion");
  assert.equal(blocks[0]?.isNewField, false);
  assert.deepEqual(
    blocks[0]?.documentTypes.map((documentType) => documentType.displayLabel),
    ["Typ 2"],
  );
});

test("required field backfill validation blocks new required fields for all active document types", () => {
  const draft = definitionDraft();

  const blocks = getRequiredFieldBackfillBlocks({
    documentTypes: [
      documentTypeFixture({ displayLabel: "Typ 2", id: "type-2" }),
      documentTypeFixture({ displayLabel: "Typ 1", id: "type-1" }),
    ],
    draft,
    existingFields: [],
  });

  assert.equal(blocks.length, 1);
  assert.equal(blocks[0]?.isNewField, true);
  assert.deepEqual(
    blocks[0]?.documentTypes.map((documentType) => documentType.displayLabel),
    ["Typ 1", "Typ 2"],
  );
});

function definitionDraft(): SystemCatalogDefinitionDraft {
  return {
    displayModes: [
      {
        isActive: true,
        isDefault: true,
        name: "Typ - Pion",
        parts: [
          {
            extensionFieldRowId: null,
            rowId: "part-base",
            separatorBefore: "",
            sourceType: "base_name",
          },
          {
            extensionFieldRowId: "field-pion",
            rowId: "part-pion",
            separatorBefore: " - ",
            sourceType: "extension_field",
          },
        ],
        rowId: "mode-default",
      },
    ],
    fields: [
      {
        code: "pion",
        dictionaryId: "dictionary-pion",
        isActive: true,
        isRequired: true,
        label: "Pion",
        mappedAttributeDefinitionId: null,
        rowId: "field-pion",
        showInOverview: true,
        valueType: "dictionary",
      },
    ],
  };
}

function systemCatalogFieldFixture(
  patch: Partial<SystemCatalogExtensionField> = {},
): SystemCatalogExtensionField {
  return {
    code: "pion",
    createdAt: "2026-07-03T10:00:00Z",
    dictionaryId: "dictionary-pion",
    fieldOrder: 0,
    id: "field-pion-id",
    isActive: true,
    isRequired: true,
    label: "Pion",
    mappedAttributeDefinitionId: null,
    showInOverview: true,
    systemCatalogKey: "document_type",
    updatedAt: "2026-07-03T10:00:00Z",
    valueType: "dictionary",
    ...patch,
  };
}

function documentTypeFixture({
  displayLabel,
  id,
  status = "active",
  values = [],
}: {
  displayLabel: string;
  id: string;
  status?: DocumentTypeDefinition["status"];
  values?: Array<{
    dictionaryEntryId: string | null;
    extensionFieldId: string;
    textValue?: string | null;
  }>;
}): DocumentTypeDefinition {
  return {
    createdAt: "2026-07-03T10:00:00Z",
    description: null,
    displayLabel,
    displayModeId: null,
    extensionValues: values.map((value) => ({
      code: "pion",
      dictionaryEntryId: value.dictionaryEntryId,
      dictionaryId: "dictionary-pion",
      displayValue: value.dictionaryEntryId,
      extensionFieldId: value.extensionFieldId,
      fieldOrder: 0,
      label: "Pion",
      showInOverview: true,
      textValue: value.textValue ?? null,
      valueType: value.textValue ? "text" : "dictionary",
    })),
    externalId: null,
    id,
    name: displayLabel,
    parameters: [],
    status,
    updatedAt: "2026-07-03T10:00:00Z",
  };
}
