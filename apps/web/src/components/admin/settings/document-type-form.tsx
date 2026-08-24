"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState, type FormEvent } from "react";

import { FieldGroup } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type {
  DictionaryEntry,
  DocumentTypeDefinition,
  SystemCatalogDefinition,
  UpsertDocumentTypeInput,
} from "@/lib/admin-settings/types";
import {
  buildDocumentTypeExtensionDraftValues,
  getActiveSystemCatalogFields,
  getMissingRequiredDocumentTypeExtensionFieldIds,
  hasDocumentTypeExtensionDraftChanges,
  toDocumentTypeExtensionValueInput,
  type DocumentTypeExtensionDraftValues,
} from "@/lib/admin-settings/view-model";

import { CatalogFormSection } from "@/components/admin/catalog/catalog-form-section";
import {
  CatalogFormActions,
  CatalogFormSheet,
} from "@/components/admin/catalog/catalog-form-sheet";
import {
  CatalogNotice,
  FieldShell,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { DocumentTypeExtensionFieldInput } from "./document-type-extension-field-input";

type DocumentTypeFormMode =
  | { kind: "create" }
  | { item: DocumentTypeDefinition; kind: "edit" };

interface DocumentTypeFormProps {
  definition: SystemCatalogDefinition | null;
  definitionError: unknown;
  dictionaryEntriesByDictionaryId: Record<string, readonly DictionaryEntry[]>;
  dictionaryEntriesError: unknown;
  dictionaryEntriesPending: boolean;
  error: unknown;
  isPending: boolean;
  mode: DocumentTypeFormMode;
  onCancel: () => void;
  onDirtyChange: (dirty: boolean) => void;
  onSubmit: (
    mode: DocumentTypeFormMode,
    input: UpsertDocumentTypeInput,
  ) => void;
}

interface DocumentTypeFormErrors {
  extensionValues: Record<string, string>;
  name?: string;
}

export function DocumentTypeForm({
  definition,
  definitionError,
  dictionaryEntriesByDictionaryId,
  dictionaryEntriesError,
  dictionaryEntriesPending,
  error,
  isPending,
  mode,
  onCancel,
  onDirtyChange,
  onSubmit,
}: DocumentTypeFormProps) {
  const t = useTranslations("AdminSettings.documentTypes.form");
  const common = useTranslations("AdminSettings.common");
  const initial = useMemo(() => {
    if (mode.kind === "create") {
      return {
        description: "",
        externalId: "",
        extensionValues: {},
        name: "",
      };
    }

    return {
      description: mode.item.description ?? "",
      externalId: mode.item.externalId ?? "",
      extensionValues: buildDocumentTypeExtensionDraftValues(mode.item),
      name: mode.item.name,
    };
  }, [mode]);
  const activeFields = useMemo(
    () => getActiveSystemCatalogFields(definition?.fields ?? []),
    [definition?.fields],
  );
  const extensionDisplayValuesByFieldId = useMemo(
    () =>
      new Map(
        mode.kind === "edit"
          ? mode.item.extensionValues.map((value) => [
              value.extensionFieldId,
              value.displayValue,
            ])
          : [],
      ),
    [mode],
  );
  const [externalId, setExternalId] = useState(initial.externalId);
  const [name, setName] = useState(initial.name);
  const [description, setDescription] = useState(initial.description);
  const [extensionValues, setExtensionValues] =
    useState<DocumentTypeExtensionDraftValues>(initial.extensionValues);
  const [errors, setErrors] = useState<DocumentTypeFormErrors>({
    extensionValues: {},
  });
  const hasExtensionErrors = Object.values(errors.extensionValues).some(
    Boolean,
  );
  const hasFormErrors = Boolean(errors.name) || hasExtensionErrors;
  const saveErrorMessage = error
    ? getCatalogErrorMessage(error, t("errors.saveFailed"))
    : null;
  const definitionErrorMessage = definitionError
    ? getCatalogErrorMessage(definitionError, t("errors.definitionLoadFailed"))
    : null;
  const dictionaryEntriesErrorMessage = dictionaryEntriesError
    ? getCatalogErrorMessage(
        dictionaryEntriesError,
        t("errors.dictionaryEntriesLoadFailed"),
      )
    : null;
  const visibleFooterError = hasFormErrors
    ? t("errors.fixFields")
    : (definitionErrorMessage ??
      dictionaryEntriesErrorMessage ??
      saveErrorMessage);
  const saveDisabled =
    !definition || dictionaryEntriesPending || Boolean(dictionaryEntriesError);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!definition) {
      setErrors({
        extensionValues: {},
        name: undefined,
      });
      return;
    }

    const nextErrors: DocumentTypeFormErrors = { extensionValues: {} };
    const normalizedName = name.trim();
    const normalizedExternalId = externalId.trim();

    if (!normalizedName) {
      nextErrors.name = t("errors.nameRequired");
    }

    for (const fieldId of getMissingRequiredDocumentTypeExtensionFieldIds(
      activeFields,
      extensionValues,
    )) {
      nextErrors.extensionValues[fieldId] = t("errors.extensionRequired");
    }

    setErrors(nextErrors);

    if (nextErrors.name || Object.keys(nextErrors.extensionValues).length > 0) {
      return;
    }

    const extensionValueInput = toDocumentTypeExtensionValueInput(
      activeFields,
      extensionValues,
    );
    const includeExtensionValues =
      mode.kind === "create" ||
      hasDocumentTypeExtensionDraftChanges(
        activeFields,
        initial.extensionValues,
        extensionValues,
      );

    onSubmit(mode, {
      description: normalizeOptionalText(description),
      externalId: normalizeOptionalText(normalizedExternalId),
      ...(includeExtensionValues
        ? { extensionValues: extensionValueInput }
        : {}),
      name: normalizedName,
    });
  }

  return (
    <CatalogFormSheet
      description={
        mode.kind === "create"
          ? t("createDescription")
          : t("editDescription", {
              id: mode.item.externalId ?? mode.item.id,
            })
      }
      footer={
        <CatalogFormActions
          cancelLabel={t("cancel")}
          error={visibleFooterError}
          isPending={isPending}
          onCancel={onCancel}
          saveDisabled={saveDisabled}
          saveLabel={t("save")}
          savingLabel={t("saving")}
        />
      }
      onSubmit={handleSubmit}
      onDirtyChange={onDirtyChange}
      title={mode.kind === "create" ? t("createTitle") : t("editTitle")}
    >
      <FieldGroup>
        <FieldShell
          error={errors.name}
          htmlFor="document-type-name"
          label={t("fields.name")}
          required
          requiredLabel={common("requiredField")}
        >
          <Input
            aria-invalid={Boolean(errors.name)}
            disabled={isPending}
            id="document-type-name"
            onChange={(event) => {
              setName(event.target.value);
              setErrors((current) => ({ ...current, name: undefined }));
            }}
            value={name}
          />
        </FieldShell>

        <FieldShell
          description={t("fields.descriptionDescription")}
          htmlFor="document-type-description"
          label={t("fields.description")}
        >
          <Textarea
            disabled={isPending}
            id="document-type-description"
            onChange={(event) => setDescription(event.target.value)}
            value={description}
          />
        </FieldShell>
      </FieldGroup>

      <section className="flex flex-col gap-3 border-t pt-4">
        <div>
          <h3 className="text-sm font-semibold">{t("parameters.title")}</h3>
          <p className="text-sm text-muted-foreground">
            {t("parameters.description")}
          </p>
        </div>

        {definitionErrorMessage ? (
          <CatalogNotice
            description={t("parameters.loadErrorDescription")}
            title={definitionErrorMessage}
            tone="danger"
          />
        ) : null}
        {dictionaryEntriesErrorMessage ? (
          <CatalogNotice
            description={t("parameters.loadErrorDescription")}
            title={dictionaryEntriesErrorMessage}
            tone="danger"
          />
        ) : null}

        {!definition ? (
          <CatalogNotice title={t("parameters.loading")} />
        ) : activeFields.length === 0 ? (
          <CatalogNotice title={t("parameters.empty")} />
        ) : (
          <FieldGroup>
            {activeFields.map((field) => (
              <DocumentTypeExtensionFieldInput
                dictionaryEntriesByDictionaryId={
                  dictionaryEntriesByDictionaryId
                }
                disabled={isPending || dictionaryEntriesPending}
                error={errors.extensionValues[field.id]}
                field={field}
                fallbackDisplayValue={
                  extensionDisplayValuesByFieldId.get(field.id) ?? null
                }
                key={field.id}
                onChange={(value) => {
                  setExtensionValues((current) => ({
                    ...current,
                    [field.id]: value,
                  }));
                  setErrors((current) => ({
                    ...current,
                    extensionValues: {
                      ...current.extensionValues,
                      [field.id]: "",
                    },
                  }));
                }}
                requiredLabel={common("requiredField")}
                value={extensionValues[field.id] ?? ""}
              />
            ))}
          </FieldGroup>
        )}
      </section>

      <CatalogFormSection
        description={t("integration.description")}
        title={t("integration.title")}
      >
        <FieldShell
          description={t("fields.externalIdDescription")}
          htmlFor="document-type-external-id"
          label={t("fields.externalId")}
        >
          <Input
            disabled={isPending}
            id="document-type-external-id"
            onChange={(event) => setExternalId(event.target.value)}
            placeholder={t("fields.externalIdPlaceholder")}
            value={externalId}
          />
        </FieldShell>
      </CatalogFormSection>
    </CatalogFormSheet>
  );
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}
