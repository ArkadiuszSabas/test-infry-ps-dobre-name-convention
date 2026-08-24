"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState, type FormEvent } from "react";

import { FieldGroup } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type {
  CustomDictionary,
  UpsertDictionaryInput,
} from "@/lib/admin-settings/types";
import { toGeneratedExternalId } from "@/lib/admin-settings/view-model";

import { CatalogFormSection } from "@/components/admin/catalog/catalog-form-section";
import {
  CatalogFormActions,
  CatalogFormSheet,
} from "@/components/admin/catalog/catalog-form-sheet";
import {
  FieldShell,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";

type DictionaryFormMode =
  | { kind: "create" }
  | { item: CustomDictionary; kind: "edit" };

interface DictionaryFormProps {
  error: unknown;
  isPending: boolean;
  mode: DictionaryFormMode;
  onCancel: () => void;
  onSubmit: (mode: DictionaryFormMode, input: UpsertDictionaryInput) => void;
}

interface DictionaryFormErrors {
  name?: string;
}

export function DictionaryForm({
  error,
  isPending,
  mode,
  onCancel,
  onSubmit,
}: DictionaryFormProps) {
  const t = useTranslations("AdminSettings.customDictionaries.form");
  const common = useTranslations("AdminSettings.common");
  const initial = useMemo(() => getInitialFormState(mode), [mode]);
  const [externalId, setExternalId] = useState(initial.externalId);
  const [name, setName] = useState(initial.name);
  const [description, setDescription] = useState(initial.description);
  const [errors, setErrors] = useState<DictionaryFormErrors>({});
  const hasFormErrors = Object.values(errors).some(Boolean);
  const saveErrorMessage = error
    ? getCatalogErrorMessage(error, t("errors.saveFailed"))
    : null;
  const visibleFooterError = hasFormErrors
    ? t("errors.fixFields")
    : saveErrorMessage;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors: DictionaryFormErrors = {};
    const normalizedExternalId = externalId.trim();
    const normalizedName = name.trim();

    if (!normalizedName) {
      nextErrors.name = t("errors.nameRequired");
    }

    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    onSubmit(mode, {
      description: normalizeOptionalText(description),
      externalId:
        normalizedExternalId ||
        toGeneratedExternalId(normalizedName, "dictionary"),
      name: normalizedName,
    });
  }

  return (
    <CatalogFormSheet
      description={
        mode.kind === "create"
          ? t("createDescription")
          : t("editDescription", { id: mode.item.externalId })
      }
      footer={
        <CatalogFormActions
          cancelLabel={t("cancel")}
          error={visibleFooterError}
          isPending={isPending}
          onCancel={onCancel}
          saveLabel={t("save")}
          savingLabel={t("saving")}
        />
      }
      onSubmit={handleSubmit}
      title={mode.kind === "create" ? t("createTitle") : t("editTitle")}
    >
      <FieldGroup>
        <FieldShell
          error={errors.name}
          htmlFor="dictionary-name"
          label={t("fields.name")}
          required
          requiredLabel={common("requiredField")}
        >
          <Input
            aria-invalid={Boolean(errors.name)}
            disabled={isPending}
            id="dictionary-name"
            onChange={(event) => {
              setName(event.target.value);
              setErrors((current) => ({ ...current, name: undefined }));
            }}
            value={name}
          />
        </FieldShell>

        <FieldShell
          htmlFor="dictionary-description"
          label={t("fields.description")}
        >
          <Textarea
            disabled={isPending}
            id="dictionary-description"
            onChange={(event) => setDescription(event.target.value)}
            value={description}
          />
        </FieldShell>
      </FieldGroup>

      <CatalogFormSection
        description={t("integration.description")}
        title={t("integration.title")}
      >
        <FieldShell
          description={t("fields.externalIdDescription")}
          htmlFor="dictionary-external-id"
          label={t("fields.externalId")}
        >
          <Input
            disabled={mode.kind === "edit" || isPending}
            id="dictionary-external-id"
            onChange={(event) => setExternalId(event.target.value)}
            placeholder={t("fields.externalIdPlaceholder")}
            value={externalId}
          />
        </FieldShell>
      </CatalogFormSection>
    </CatalogFormSheet>
  );
}

function getInitialFormState(mode: DictionaryFormMode) {
  if (mode.kind === "create") {
    return {
      description: "",
      externalId: "",
      name: "",
    };
  }

  return {
    description: mode.item.description ?? "",
    externalId: mode.item.externalId,
    name: mode.item.name,
  };
}

function normalizeOptionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}
