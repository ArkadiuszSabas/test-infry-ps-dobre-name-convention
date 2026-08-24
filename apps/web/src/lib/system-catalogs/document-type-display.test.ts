import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { SystemCatalogDefinition } from "@/lib/system-catalogs/types";

import {
  type DocumentTypeDisplayItem,
  formatDocumentTypeDisplayLabel,
  getDocumentTypeDisplayModeOptions,
  resolveDocumentTypeDisplayModeId,
  shouldShowDocumentTypeDisplayModeSelect,
} from "./document-type-display";

const DOCUMENT_TYPE_ID = "11111111-1111-1111-1111-111111111111";
const PION_FIELD_ID = "22222222-2222-2222-2222-222222222222";
const DEFAULT_DISPLAY_MODE_ID = "33333333-3333-3333-3333-333333333333";
const REVERSE_DISPLAY_MODE_ID = "44444444-4444-4444-4444-444444444444";
const DICTIONARY_ID = "55555555-5555-5555-5555-555555555555";

describe("document type display", () => {
  it("uses the document type name when there are no extension fields", () => {
    const definition = definitionFixture({ fields: [], modes: [] });

    assert.equal(
      formatDocumentTypeDisplayLabel({
        definition,
        documentType: documentTypeFixture({ extensionValues: [] }),
      }),
      "Typ 1",
    );
    assert.equal(shouldShowDocumentTypeDisplayModeSelect(definition), false);
  });

  it("uses the document type name as a fallback when there are no display modes", () => {
    const definition = definitionFixture({ modes: [] });

    assert.equal(
      formatDocumentTypeDisplayLabel({
        definition,
        documentType: documentTypeFixture(),
      }),
      "Typ 1",
    );
    assert.equal(shouldShowDocumentTypeDisplayModeSelect(definition), false);
  });

  it("preserves backend labels while display definition is unavailable", () => {
    assert.equal(
      formatDocumentTypeDisplayLabel({
        definition: null,
        documentType: documentTypeFixture({
          displayLabel: "Typ 1 - Pion1",
        }),
      }),
      "Typ 1 - Pion1",
    );
  });

  it("uses the single active display mode without requiring a mode selector", () => {
    const definition = definitionFixture({
      modes: [displayModeFixture({ id: DEFAULT_DISPLAY_MODE_ID })],
    });

    assert.equal(
      resolveDocumentTypeDisplayModeId({ definition }),
      DEFAULT_DISPLAY_MODE_ID,
    );
    assert.equal(
      formatDocumentTypeDisplayLabel({
        definition,
        displayModeId: DEFAULT_DISPLAY_MODE_ID,
        documentType: documentTypeFixture(),
      }),
      "Typ 1 - Pion1",
    );
    assert.deepEqual(getDocumentTypeDisplayModeOptions(definition), [
      { id: DEFAULT_DISPLAY_MODE_ID, label: "Typ - Pion" },
    ]);
    assert.equal(shouldShowDocumentTypeDisplayModeSelect(definition), false);
  });

  it("switches labels when more than one active display mode exists", () => {
    const definition = definitionFixture({
      modes: [
        displayModeFixture({ id: DEFAULT_DISPLAY_MODE_ID }),
        displayModeFixture({
          id: REVERSE_DISPLAY_MODE_ID,
          isDefault: false,
          name: "Pion - Typ",
          reverse: true,
        }),
      ],
    });

    assert.equal(shouldShowDocumentTypeDisplayModeSelect(definition), true);
    assert.equal(
      resolveDocumentTypeDisplayModeId({ definition }),
      DEFAULT_DISPLAY_MODE_ID,
    );
    assert.equal(
      formatDocumentTypeDisplayLabel({
        definition,
        displayModeId: REVERSE_DISPLAY_MODE_ID,
        documentType: documentTypeFixture(),
      }),
      "Pion1 - Typ 1",
    );
  });
});

function definitionFixture({
  fields = [pionFieldFixture()],
  modes = [displayModeFixture({ id: DEFAULT_DISPLAY_MODE_ID })],
}: {
  fields?: SystemCatalogDefinition["fields"];
  modes?: SystemCatalogDefinition["displayModes"];
} = {}): SystemCatalogDefinition {
  return {
    displayModes: modes,
    fields,
    systemCatalogKey: "document_type",
  };
}

function pionFieldFixture(): SystemCatalogDefinition["fields"][number] {
  return {
    code: "pion",
    createdAt: "2026-07-06T10:00:00Z",
    dictionaryId: DICTIONARY_ID,
    fieldOrder: 0,
    id: PION_FIELD_ID,
    isActive: true,
    isRequired: false,
    label: "Pion",
    mappedAttributeDefinitionId: null,
    showInOverview: true,
    systemCatalogKey: "document_type",
    updatedAt: "2026-07-06T10:00:00Z",
    valueType: "dictionary",
  };
}

function displayModeFixture({
  id,
  isDefault = true,
  name = "Typ - Pion",
  reverse = false,
}: {
  id: string;
  isDefault?: boolean;
  name?: string;
  reverse?: boolean;
}): SystemCatalogDefinition["displayModes"][number] {
  const basePart = {
    displayModeId: id,
    extensionFieldId: null,
    id: `${id}-base`,
    partOrder: reverse ? 1 : 0,
    separatorBefore: reverse ? " - " : null,
    sourceType: "base_name" as const,
  };
  const fieldPart = {
    displayModeId: id,
    extensionFieldId: PION_FIELD_ID,
    id: `${id}-pion`,
    partOrder: reverse ? 0 : 1,
    separatorBefore: reverse ? null : " - ",
    sourceType: "extension_field" as const,
  };

  return {
    createdAt: "2026-07-06T10:00:00Z",
    id,
    isActive: true,
    isDefault,
    name,
    parts: reverse ? [fieldPart, basePart] : [basePart, fieldPart],
    systemCatalogKey: "document_type",
    updatedAt: "2026-07-06T10:00:00Z",
  };
}

function documentTypeFixture({
  displayLabel = "Typ 1",
  extensionValues = [
    {
      displayValue: "Pion1",
      extensionFieldId: PION_FIELD_ID,
      textValue: null,
    },
  ],
}: {
  displayLabel?: string;
  extensionValues?: DocumentTypeDisplayItem["extensionValues"];
} = {}): DocumentTypeDisplayItem {
  return {
    displayLabel,
    extensionValues,
    externalId: "typ_1",
    id: DOCUMENT_TYPE_ID,
    name: "Typ 1",
    parameters: [
      {
        code: "pion",
        label: "Pion",
        value: "Pion1",
      },
    ],
  };
}
