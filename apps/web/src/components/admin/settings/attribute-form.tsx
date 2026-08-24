"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState, type FormEvent } from "react";

import {
  CatalogFormActions,
  CatalogFormSheet,
} from "@/components/admin/catalog/catalog-form-sheet";
import {
  FieldShell,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { FieldGroup } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { Textarea } from "@/components/ui/textarea";
import type {
  AttributeCategory,
  AttributeSource,
  AttributeValueSource,
  CustomDictionary,
  UpdateAttributeInput,
  UpsertAttributeInput,
  WritableAttributeDataType,
} from "@/lib/admin-settings/types";
import { parseAllowedValues } from "@/lib/admin-settings/view-model";

import {
  buildConstraints,
  getEffectiveAttributeDataType,
  getInitialFormState,
  getLlmContextUpdate,
  isAttributeSource,
  isAttributeValueSource,
  isWritableAttributeDataType,
  normalizeOptionalText,
  type AttributeFormErrors,
  type AttributeFormMode,
} from "./attribute-form-model";
import {
  AttributeIntegrationSection,
  AttributeLlmContextSection,
  AttributeValidationSection,
} from "./attribute-form-sections";
import { AttributeValueSourceFields } from "./attribute-value-source-fields";

interface AttributeFormProps {
  attributeCategories: AttributeCategory[];
  attributeCategoryEntriesLoading: boolean;
  error: unknown;
  dictionaries: CustomDictionary[];
  dictionariesLoading: boolean;
  isPending: boolean;
  mode: AttributeFormMode;
  onCancel: () => void;
  onDirtyChange: (dirty: boolean) => void;
  onSubmit: (
    mode: AttributeFormMode,
    input: UpsertAttributeInput | UpdateAttributeInput,
  ) => void;
}

export function AttributeForm({
  attributeCategories,
  attributeCategoryEntriesLoading,
  dictionaries,
  dictionariesLoading,
  error,
  isPending,
  mode,
  onCancel,
  onDirtyChange,
  onSubmit,
}: AttributeFormProps) {
  const t = useTranslations("AdminSettings.attributes.form");
  const common = useTranslations("AdminSettings.common");
  const collection = useTranslations("CollectionView");
  const initial = useMemo(() => getInitialFormState(mode), [mode]);
  const [externalId, setExternalId] = useState(initial.externalId);
  const [name, setName] = useState(initial.name);
  const [categoryId, setCategoryId] = useState(initial.categoryId);
  const [source, setSource] = useState<AttributeSource>(initial.source);
  const [valueSource, setValueSource] = useState<AttributeValueSource>(
    initial.valueSource,
  );
  const [dictionaryId, setDictionaryId] = useState(initial.dictionaryId);
  const [dataType, setDataType] = useState<WritableAttributeDataType>(
    initial.dataType,
  );
  const [dataTypeChanged, setDataTypeChanged] = useState(false);
  const [minLength, setMinLength] = useState(initial.minLength);
  const [maxLength, setMaxLength] = useState(initial.maxLength);
  const [pattern, setPattern] = useState(initial.pattern);
  const [minValue, setMinValue] = useState(initial.minValue);
  const [maxValue, setMaxValue] = useState(initial.maxValue);
  const [allowedValues, setAllowedValues] = useState(initial.allowedValues);
  const [comment, setComment] = useState(initial.comment);
  const [llmContext, setLlmContext] = useState(initial.llmContext);
  const [errors, setErrors] = useState<AttributeFormErrors>({});
  const effectiveDataType = getEffectiveAttributeDataType(
    valueSource,
    dataType,
  );
  const hasFormErrors = Object.values(errors).some(Boolean);
  const saveErrorMessage = error
    ? getCatalogErrorMessage(error, t("errors.saveFailed"))
    : null;
  const visibleFooterError = hasFormErrors
    ? t("errors.fixFields")
    : saveErrorMessage;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors: AttributeFormErrors = {};
    const normalizedName = name.trim();
    const normalizedExternalId = externalId.trim();
    const selectedCategory =
      attributeCategories.find((entry) => entry.id === categoryId) ?? null;
    const nextAllowedValues =
      valueSource === "inline_allowed_values"
        ? parseAllowedValues(allowedValues)
        : [];
    const nextDictionaryId =
      valueSource === "dictionary" ? normalizeOptionalText(dictionaryId) : null;
    const constraints =
      valueSource === "dictionary"
        ? {}
        : buildConstraints(
            nextErrors,
            { maxLength, maxValue, minLength, minValue, pattern },
            {
              integer: t("errors.integer"),
              number: t("errors.number"),
            },
            effectiveDataType,
          );

    if (!normalizedName) {
      nextErrors.name = t("errors.nameRequired");
    }

    if (!selectedCategory) {
      nextErrors.category = t("errors.categoryRequired");
    }

    if (
      valueSource === "inline_allowed_values" &&
      nextAllowedValues.length === 0
    ) {
      nextErrors.allowedValues = t("errors.allowedValuesRequired");
    }

    if (valueSource === "dictionary" && !nextDictionaryId) {
      nextErrors.dictionaryId = t("errors.dictionaryRequired");
    }

    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    onSubmit(mode, {
      allowedValues: nextAllowedValues,
      categoryId: selectedCategory?.id ?? null,
      comment: normalizeOptionalText(comment),
      constraints,
      dataType:
        mode.kind === "create" || dataTypeChanged || valueSource !== "free_text"
          ? effectiveDataType
          : undefined,
      dictionaryId: nextDictionaryId,
      ...getLlmContextUpdate(mode, llmContext),
      externalId: normalizeOptionalText(normalizedExternalId),
      name: normalizedName,
      source,
      valueSource,
    });
  }

  function handleSourceChange(value: string) {
    if (isAttributeSource(value)) {
      setSource(value);
    }
  }

  function handleDataTypeChange(value: string) {
    if (isWritableAttributeDataType(value)) {
      setDataType(value);
      setDataTypeChanged(true);
      setErrors(clearConstraintErrors);
    }
  }

  function handleValueSourceChange(value: string) {
    if (isAttributeValueSource(value)) {
      setValueSource(value);
      setErrors((current) =>
        clearConstraintErrors({
          ...current,
          allowedValues: undefined,
          dictionaryId: undefined,
        }),
      );

      if (value === "dictionary" || value === "inline_allowed_values") {
        setDataType("string");
        setDataTypeChanged(true);
      }

      if (value === "dictionary") {
        setAllowedValues("");
      } else {
        setDictionaryId("");
      }
    }
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
          htmlFor="attribute-name"
          label={t("fields.name")}
          required
          requiredLabel={common("requiredField")}
        >
          <Input
            aria-invalid={Boolean(errors.name)}
            disabled={isPending}
            id="attribute-name"
            onChange={(event) => {
              setName(event.target.value);
              setErrors((current) => ({ ...current, name: undefined }));
            }}
            value={name}
          />
        </FieldShell>

        <FieldShell
          error={errors.category}
          htmlFor="attribute-category"
          label={t("fields.category")}
          required
          requiredLabel={common("requiredField")}
        >
          <SearchableSelect
            ariaLabel={t("fields.category")}
            disabled={isPending || attributeCategoryEntriesLoading}
            emptyMessage={collection("noResults")}
            id="attribute-category"
            invalid={Boolean(errors.category)}
            onValueChange={(value) => {
              setCategoryId(value);
              setErrors((current) => ({ ...current, category: undefined }));
            }}
            options={attributeCategories.map((entry) => ({
              description: entry.externalId ?? undefined,
              label: entry.label,
              value: entry.id,
            }))}
            placeholder={t("fields.categoryPlaceholder")}
            searchPlaceholder={collection("search")}
            triggerClassName="w-full"
            value={categoryId || undefined}
          />
        </FieldShell>

        <AttributeValueSourceFields
          dataType={dataType}
          dictionaries={dictionaries}
          dictionariesLoading={dictionariesLoading}
          dictionaryError={errors.dictionaryId}
          dictionaryId={dictionaryId}
          isPending={isPending}
          onDataTypeChange={handleDataTypeChange}
          onDictionaryChange={(value) => {
            setDictionaryId(value);
            setErrors((current) => ({
              ...current,
              dictionaryId: undefined,
            }));
          }}
          onValueSourceChange={handleValueSourceChange}
          valueSource={valueSource}
        />

        {valueSource === "inline_allowed_values" ? (
          <FieldShell
            error={errors.allowedValues}
            htmlFor="attribute-allowed-values"
            label={t("fields.allowedValues")}
            required
            requiredLabel={common("requiredField")}
          >
            <Textarea
              aria-invalid={Boolean(errors.allowedValues)}
              disabled={isPending}
              id="attribute-allowed-values"
              onChange={(event) => {
                setAllowedValues(event.target.value);
                setErrors((current) => ({
                  ...current,
                  allowedValues: undefined,
                }));
              }}
              value={allowedValues}
            />
          </FieldShell>
        ) : null}
      </FieldGroup>

      <AttributeLlmContextSection
        isPending={isPending}
        llmContext={llmContext}
        onLlmContextChange={setLlmContext}
      />

      <AttributeIntegrationSection
        comment={comment}
        externalId={externalId}
        isPending={isPending}
        onCommentChange={setComment}
        onExternalIdChange={setExternalId}
        onSourceChange={handleSourceChange}
        source={source}
      />

      <AttributeValidationSection
        dataType={effectiveDataType}
        errors={errors}
        isPending={isPending}
        maxLength={maxLength}
        maxValue={maxValue}
        minLength={minLength}
        minValue={minValue}
        onErrorClear={(key) =>
          setErrors((current) => ({ ...current, [key]: undefined }))
        }
        onMaxLengthChange={setMaxLength}
        onMaxValueChange={setMaxValue}
        onMinLengthChange={setMinLength}
        onMinValueChange={setMinValue}
        onPatternChange={setPattern}
        pattern={pattern}
        valueSource={valueSource}
      />
    </CatalogFormSheet>
  );
}

function clearConstraintErrors(
  errors: AttributeFormErrors,
): AttributeFormErrors {
  return {
    ...errors,
    maxLength: undefined,
    maxValue: undefined,
    minLength: undefined,
    minValue: undefined,
  };
}
