"use client";

import { useTranslations } from "next-intl";

import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { SearchableSelect } from "@/components/ui/searchable-select";
import type {
  ManualUploadDictionaryEntry,
  ManualUploadMetadataField,
} from "@/lib/inbox/types";
import { cn } from "@/lib/utils";

interface ManualUploadMetadataSectionProps {
  dictionaryOptionsById: Record<string, readonly ManualUploadDictionaryEntry[]>;
  disabled: boolean;
  errors: Record<string, string>;
  fields: readonly ManualUploadMetadataField[];
  onChange: (field: ManualUploadMetadataField, value: string) => void;
  requirement: "optional" | "required";
  values: Record<string, string>;
}

export function ManualUploadMetadataSection({
  dictionaryOptionsById,
  disabled,
  errors,
  fields,
  onChange,
  requirement,
  values,
}: ManualUploadMetadataSectionProps) {
  const t = useTranslations("Inbox");

  if (fields.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border bg-background">
      <div className="border-b px-4 py-3">
        <div className="min-w-0">
          <p className="text-sm font-medium">
            {t(`upload.metadata.groups.${requirement}.title`)}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {t(`upload.metadata.groups.${requirement}.description`)}
          </p>
        </div>
      </div>
      <div className="flex flex-col gap-3 p-4">
        {fields.map((field) => (
          <ManualUploadMetadataFieldControl
            dictionaryOptions={
              field.dictionaryId
                ? (dictionaryOptionsById[field.dictionaryId] ?? [])
                : []
            }
            disabled={disabled}
            error={errors[field.key]}
            field={field}
            key={field.key}
            onChange={(value) => onChange(field, value)}
            value={values[field.key] ?? ""}
          />
        ))}
      </div>
    </div>
  );
}

interface ManualUploadMetadataFieldControlProps {
  dictionaryOptions: readonly ManualUploadDictionaryEntry[];
  disabled: boolean;
  error?: string;
  field: ManualUploadMetadataField;
  onChange: (value: string) => void;
  value: string;
}

function ManualUploadMetadataFieldControl({
  dictionaryOptions,
  disabled,
  error,
  field,
  onChange,
  value,
}: ManualUploadMetadataFieldControlProps) {
  const t = useTranslations("Inbox");
  const collection = useTranslations("CollectionView");
  const fieldId = `upload-metadata-${field.key}`;
  const selectOptions = getMetadataSelectOptions(field, dictionaryOptions);
  const isSelectField =
    field.dataType === "boolean" ||
    field.valueSource === "dictionary" ||
    field.valueSource === "inline_allowed_values";
  const isEmptyConstrainedSelect =
    field.dataType !== "boolean" && selectOptions.length === 0;
  const searchableSelectOptions =
    field.dataType === "boolean"
      ? [
          { label: t("upload.metadata.boolean.true"), value: "true" },
          { label: t("upload.metadata.boolean.false"), value: "false" },
        ]
      : selectOptions;

  return (
    <Field
      className={cn(
        "rounded-lg border bg-muted/10 p-3",
        error && "border-destructive/50 bg-destructive/5",
      )}
    >
      <div className="min-w-0">
        <FieldLabel htmlFor={fieldId}>{field.label}</FieldLabel>
        <FieldDescription>
          {field.category}
          {" \u00b7 "}
          {t(`upload.metadata.types.${field.dataType}`)}
        </FieldDescription>
      </div>
      {isSelectField ? (
        <SearchableSelect
          ariaLabel={field.label}
          disabled={disabled || isEmptyConstrainedSelect}
          emptyMessage={collection("noResults")}
          id={fieldId}
          invalid={Boolean(error)}
          onValueChange={onChange}
          options={searchableSelectOptions}
          placeholder={t("upload.metadata.placeholder")}
          searchPlaceholder={collection("search")}
          sortOptions={false}
          triggerClassName="w-full"
          value={value || undefined}
        />
      ) : (
        <Input
          aria-invalid={Boolean(error)}
          disabled={disabled}
          id={fieldId}
          onChange={(event) => onChange(event.target.value)}
          required={field.required}
          step={inputStepForMetadataField(field)}
          type={inputTypeForMetadataField(field)}
          value={value}
        />
      )}
      {error ? (
        <FieldDescription className="font-medium text-destructive">
          {error}
        </FieldDescription>
      ) : null}
    </Field>
  );
}

function getMetadataSelectOptions(
  field: ManualUploadMetadataField,
  dictionaryOptions: readonly ManualUploadDictionaryEntry[],
) {
  if (field.valueSource === "dictionary") {
    return dictionaryOptions.map((entry) => ({
      label: entry.label,
      value: entry.externalId,
    }));
  }

  if (field.valueSource === "inline_allowed_values") {
    return field.allowedValues.map((value) => ({ label: value, value }));
  }

  return [];
}

function inputTypeForMetadataField(field: ManualUploadMetadataField) {
  if (field.dataType === "date") {
    return "date";
  }
  if (field.dataType === "datetime") {
    return "datetime-local";
  }
  if (field.dataType === "integer" || field.dataType === "number") {
    return "number";
  }
  return "text";
}

function inputStepForMetadataField(field: ManualUploadMetadataField) {
  return field.dataType === "number" ? "any" : undefined;
}
