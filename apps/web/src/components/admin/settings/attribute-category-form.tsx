"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState, type FormEvent } from "react";

import { CatalogFormSection } from "@/components/admin/catalog/catalog-form-section";
import {
  CatalogFormActions,
  CatalogFormSheet,
} from "@/components/admin/catalog/catalog-form-sheet";
import {
  FieldShell,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type {
  AttributeCategory,
  UpdateAttributeCategoryInput,
  UpsertAttributeCategoryInput,
} from "@/lib/admin-settings/types";

import { IS_METADATA_FLAG } from "./attribute-category-flag-badges";

export type AttributeCategoryFormMode =
  | { kind: "create" }
  | { item: AttributeCategory; kind: "edit" };

interface AttributeCategoryFormProps {
  error: unknown;
  isPending: boolean;
  mode: AttributeCategoryFormMode;
  onCancel: () => void;
  onDirtyChange: (dirty: boolean) => void;
  onSubmit: (
    mode: AttributeCategoryFormMode,
    input: UpsertAttributeCategoryInput | UpdateAttributeCategoryInput,
  ) => void;
}

interface AttributeCategoryFormErrors {
  externalId?: string;
  label?: string;
}

export function AttributeCategoryForm({
  error,
  isPending,
  mode,
  onCancel,
  onDirtyChange,
  onSubmit,
}: AttributeCategoryFormProps) {
  const t = useTranslations("AdminSettings.attributeCategories.form");
  const common = useTranslations("AdminSettings.common");
  const initial = useMemo(() => getInitialFormState(mode), [mode]);
  const [externalId, setExternalId] = useState(initial.externalId);
  const [label, setLabel] = useState(initial.label);
  const [isMetadata, setIsMetadata] = useState(initial.isMetadata);
  const [errors, setErrors] = useState<AttributeCategoryFormErrors>({});
  const hasFormErrors = Object.values(errors).some(Boolean);
  const saveErrorMessage = error
    ? getCatalogErrorMessage(error, t("errors.saveFailed"))
    : null;
  const visibleFooterError = hasFormErrors
    ? t("errors.fixFields")
    : saveErrorMessage;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors: AttributeCategoryFormErrors = {};
    const normalizedLabel = label.trim();
    const normalizedExternalId = externalId.trim();

    if (!normalizedLabel) {
      nextErrors.label = t("errors.labelRequired");
    }

    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    onSubmit(mode, {
      ...(mode.kind === "create"
        ? { externalId: normalizedExternalId || null }
        : {}),
      flags: {
        ...(mode.kind === "edit" ? mode.item.flags : {}),
        [IS_METADATA_FLAG]: isMetadata,
      },
      label: normalizedLabel,
    });
  }

  return (
    <CatalogFormSheet
      description={
        mode.kind === "create"
          ? t("createDescription")
          : t("editDescription", {
              id: mode.item.externalId,
            })
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
      onDirtyChange={onDirtyChange}
      title={mode.kind === "create" ? t("createTitle") : t("editTitle")}
    >
      <FieldGroup>
        <FieldShell
          error={errors.label}
          htmlFor="attribute-category-label"
          label={t("fields.label")}
          required
          requiredLabel={common("requiredField")}
        >
          <Input
            aria-invalid={Boolean(errors.label)}
            disabled={isPending}
            id="attribute-category-label"
            onChange={(event) => {
              setLabel(event.target.value);
              setErrors((current) => ({ ...current, label: undefined }));
            }}
            value={label}
          />
        </FieldShell>
      </FieldGroup>

      <CatalogFormSection
        description={t("integration.description")}
        title={t("integration.title")}
      >
        <FieldGroup>
          <FieldShell
            description={t("fields.externalIdDescription")}
            error={errors.externalId}
            htmlFor="attribute-category-external-id"
            label={t("fields.externalId")}
          >
            <Input
              aria-invalid={Boolean(errors.externalId)}
              disabled={isPending || mode.kind === "edit"}
              id="attribute-category-external-id"
              onChange={(event) => {
                setExternalId(event.target.value);
                setErrors((current) => ({
                  ...current,
                  externalId: undefined,
                }));
              }}
              placeholder={
                mode.kind === "create"
                  ? t("fields.externalIdPlaceholder")
                  : undefined
              }
              value={externalId}
            />
          </FieldShell>
        </FieldGroup>
      </CatalogFormSection>

      <CatalogFormSection
        description={t("flags.description")}
        title={t("flags.title")}
      >
        <Field orientation="horizontal">
          <Checkbox
            checked={isMetadata}
            disabled={isPending}
            id="attribute-category-is-metadata"
            onCheckedChange={(checked) => {
              setIsMetadata(checked === true);
            }}
          />
          <div className="grid gap-1">
            <FieldLabel
              className="font-normal"
              htmlFor="attribute-category-is-metadata"
            >
              {t("fields.isMetadata")}
            </FieldLabel>
            <FieldDescription>
              {t("fields.isMetadataDescription")}
            </FieldDescription>
          </div>
        </Field>
      </CatalogFormSection>
    </CatalogFormSheet>
  );
}

function getInitialFormState(mode: AttributeCategoryFormMode) {
  if (mode.kind === "create") {
    return {
      externalId: "",
      isMetadata: false,
      label: "",
    };
  }

  return {
    externalId: mode.item.externalId,
    isMetadata: mode.item.flags[IS_METADATA_FLAG] === true,
    label: mode.item.label,
  };
}
