"use client";

import { PlusIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import type {
  AttributeDefinition,
  CustomDictionary,
  DocumentTypeDefinition,
  SaveSystemCatalogDefinitionInput,
  SystemCatalogDefinition,
} from "@/lib/admin-settings/types";
import {
  buildSystemCatalogDefinitionDraft,
  toSaveSystemCatalogDefinitionInput,
  type SystemCatalogDefinitionDraft,
  type SystemCatalogDisplayModeDraft,
  type SystemCatalogFieldDraft,
} from "@/lib/admin-settings/view-model";

import {
  CatalogFormActions,
  CatalogFormSheet,
} from "@/components/admin/catalog/catalog-form-sheet";
import {
  CatalogNotice,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { RequiredFieldBackfillNotice } from "./document-type-definition-backfill-notice";
import { DisplayModeDraftRow } from "./document-type-definition-display-mode-row";
import { FieldDraftRow } from "./document-type-definition-field-row";
import {
  clearDisplayModeFieldReferences,
  createDraftId,
  createModePart,
  getDefinitionDraftError,
  getRequiredFieldBackfillBlocks,
  moveField,
  moveMode,
  type RequiredFieldBackfillBlock,
} from "./document-type-definition-ui-helpers";

interface DocumentTypeDefinitionDrawerProps {
  activeAttributes: readonly AttributeDefinition[];
  activeDictionaries: readonly CustomDictionary[];
  definition: SystemCatalogDefinition | null;
  documentTypes: readonly DocumentTypeDefinition[];
  error: unknown;
  isLoading: boolean;
  isPending: boolean;
  loadError: unknown;
  onCancel: () => void;
  onEditDocumentType: (documentType: DocumentTypeDefinition) => void;
  onSubmit: (input: SaveSystemCatalogDefinitionInput) => void;
}

export function DocumentTypeDefinitionDrawer({
  activeAttributes,
  activeDictionaries,
  definition,
  documentTypes,
  error,
  isLoading,
  isPending,
  loadError,
  onCancel,
  onEditDocumentType,
  onSubmit,
}: DocumentTypeDefinitionDrawerProps) {
  const t = useTranslations("AdminSettings.documentTypes.definition");
  const [draft, setDraft] = useState<SystemCatalogDefinitionDraft | null>(() =>
    definition ? buildSystemCatalogDefinitionDraft(definition) : null,
  );
  const [formError, setFormError] = useState<string | null>(null);
  const [requiredBackfillBlocks, setRequiredBackfillBlocks] = useState<
    RequiredFieldBackfillBlock[]
  >([]);
  const isDisabled = isPending || isLoading || Boolean(loadError) || !draft;
  const saveError = error
    ? getCatalogErrorMessage(error, t("errors.saveFailed"))
    : null;
  const visibleFooterError =
    requiredBackfillBlocks.length > 0
      ? t("errors.requiredBackfillFooter")
      : (formError ?? saveError);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!draft) {
      setFormError(t("errors.definitionRequired"));
      return;
    }

    if (loadError) {
      setFormError(getCatalogErrorMessage(loadError, t("errors.loadFailed")));
      return;
    }

    const validationError = getDefinitionDraftError(draft, t);
    setFormError(validationError);
    setRequiredBackfillBlocks([]);

    if (validationError) {
      return;
    }

    const nextBackfillBlocks = getRequiredFieldBackfillBlocks({
      documentTypes,
      draft,
      existingFields: definition?.fields ?? [],
    });
    setRequiredBackfillBlocks(nextBackfillBlocks);

    if (nextBackfillBlocks.length > 0) {
      return;
    }

    onSubmit(toSaveSystemCatalogDefinitionInput(draft));
  }

  function updateField(rowId: string, patch: Partial<SystemCatalogFieldDraft>) {
    setDraft((current) => {
      if (!current) {
        return current;
      }

      const nextDraft = {
        ...current,
        fields: current.fields.map((field) =>
          field.rowId === rowId ? { ...field, ...patch } : field,
        ),
      };

      return patch.isActive === false
        ? clearDisplayModeFieldReferences(nextDraft, rowId)
        : nextDraft;
    });
    clearLocalErrors();
  }

  function updateMode(
    rowId: string,
    patch: Partial<SystemCatalogDisplayModeDraft>,
  ) {
    setDraft((current) =>
      current
        ? {
            ...current,
            displayModes: current.displayModes.map((mode) =>
              mode.rowId === rowId
                ? { ...mode, ...patch }
                : patch.isDefault
                  ? { ...mode, isDefault: false }
                  : mode,
            ),
          }
        : current,
    );
    clearLocalErrors();
  }

  function addField() {
    const rowNumber = (draft?.fields.length ?? 0) + 1;
    setDraft((current) => ({
      displayModes: current?.displayModes ?? [],
      fields: [
        ...(current?.fields ?? []),
        {
          code: `pole_${rowNumber}`,
          dictionaryId: null,
          isActive: true,
          isRequired: false,
          label: "",
          mappedAttributeDefinitionId: null,
          rowId: createDraftId("field"),
          showInOverview: false,
          valueType: "text",
        },
      ],
    }));
    clearLocalErrors();
  }

  function addMode() {
    setDraft((current) => ({
      displayModes: [
        ...(current?.displayModes ?? []),
        {
          isActive: true,
          isDefault: (current?.displayModes ?? []).length === 0,
          name: "",
          parts: [createModePart("base_name")],
          rowId: createDraftId("mode"),
        },
      ],
      fields: current?.fields ?? [],
    }));
    clearLocalErrors();
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
          saveDisabled={isDisabled}
          saveLabel={t("save")}
          savingLabel={t("saving")}
        />
      }
      onSubmit={handleSubmit}
      title={t("title")}
    >
      {loadError ? (
        <CatalogNotice
          description={t("errors.loadDescription")}
          title={getCatalogErrorMessage(loadError, t("errors.loadFailed"))}
          tone="danger"
        />
      ) : null}
      {requiredBackfillBlocks.length > 0 ? (
        <RequiredFieldBackfillNotice
          blocks={requiredBackfillBlocks}
          onEditDocumentType={onEditDocumentType}
        />
      ) : null}

      <section className="flex flex-col gap-3">
        <SectionHeading
          description={t("fields.description")}
          title={t("fields.title")}
        />
        <div className="flex flex-col gap-3">
          {draft?.fields.map((field, index) => (
            <FieldDraftRow
              activeAttributes={activeAttributes}
              activeDictionaries={activeDictionaries}
              disabled={isPending}
              field={field}
              isFirst={index === 0}
              isLast={index === draft.fields.length - 1}
              key={field.rowId}
              onMoveDown={() => setDraft(moveField(draft, index, 1))}
              onMoveUp={() => setDraft(moveField(draft, index, -1))}
              onRemove={field.id ? undefined : () => removeField(field.rowId)}
              onUpdate={(patch) => updateField(field.rowId, patch)}
            />
          ))}
          {draft?.fields.length === 0 ? (
            <CatalogNotice title={t("fields.empty")} />
          ) : null}
        </div>
        <Button
          className="self-start"
          disabled={isPending}
          onClick={addField}
          type="button"
          variant="outline"
        >
          <PlusIcon data-icon="inline-start" />
          {t("fields.add")}
        </Button>
      </section>

      <section className="flex flex-col gap-3 border-t pt-4">
        <SectionHeading
          description={t("displayModes.description")}
          title={t("displayModes.title")}
        />
        <div className="flex flex-col gap-3">
          {draft?.displayModes.map((mode, index) => (
            <DisplayModeDraftRow
              disabled={isPending}
              fields={draft.fields}
              isFirst={index === 0}
              isLast={index === draft.displayModes.length - 1}
              key={mode.rowId}
              mode={mode}
              onAddPart={(sourceType) =>
                updateMode(mode.rowId, {
                  parts: [...mode.parts, createModePart(sourceType)],
                })
              }
              onMoveDown={() => setDraft(moveMode(draft, index, 1))}
              onMoveUp={() => setDraft(moveMode(draft, index, -1))}
              onRemove={() => removeMode(mode.rowId)}
              onUpdate={(patch) => updateMode(mode.rowId, patch)}
            />
          ))}
          {draft?.displayModes.length === 0 ? (
            <CatalogNotice title={t("displayModes.empty")} />
          ) : null}
        </div>
        <Button
          className="self-start"
          disabled={isPending}
          onClick={addMode}
          type="button"
          variant="outline"
        >
          <PlusIcon data-icon="inline-start" />
          {t("displayModes.add")}
        </Button>
      </section>
    </CatalogFormSheet>
  );

  function removeField(rowId: string) {
    setDraft((current) => {
      if (!current) {
        return current;
      }

      return clearDisplayModeFieldReferences(
        {
          ...current,
          fields: current.fields.filter((field) => field.rowId !== rowId),
        },
        rowId,
      );
    });
    clearLocalErrors();
  }

  function removeMode(rowId: string) {
    setDraft((current) =>
      current
        ? {
            ...current,
            displayModes: current.displayModes.filter(
              (mode) => mode.rowId !== rowId,
            ),
          }
        : current,
    );
    clearLocalErrors();
  }

  function clearLocalErrors() {
    setFormError(null);
    setRequiredBackfillBlocks([]);
  }
}

interface SectionHeadingProps {
  description: string;
  title: string;
}

function SectionHeading({ description, title }: SectionHeadingProps) {
  return (
    <div>
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
