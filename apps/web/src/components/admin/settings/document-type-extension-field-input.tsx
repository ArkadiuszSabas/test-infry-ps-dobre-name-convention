"use client";

import { useTranslations } from "next-intl";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  DictionaryEntry,
  SystemCatalogExtensionField,
} from "@/lib/admin-settings/types";

import { FieldShell } from "@/components/admin/catalog/catalog-shared";

const NONE_VALUE = "__none";

interface DocumentTypeExtensionFieldInputProps {
  dictionaryEntriesByDictionaryId: Record<string, readonly DictionaryEntry[]>;
  disabled: boolean;
  error?: string;
  fallbackDisplayValue: string | null;
  field: SystemCatalogExtensionField;
  onChange: (value: string) => void;
  requiredLabel: string;
  value: string;
}

export function DocumentTypeExtensionFieldInput({
  dictionaryEntriesByDictionaryId,
  disabled,
  error,
  fallbackDisplayValue,
  field,
  onChange,
  requiredLabel,
  value,
}: DocumentTypeExtensionFieldInputProps) {
  const t = useTranslations("AdminSettings.documentTypes.form.parameters");
  const entries = field.dictionaryId
    ? (dictionaryEntriesByDictionaryId[field.dictionaryId] ?? [])
    : [];
  const hasCurrentEntry = entries.some((entry) => entry.id === value);

  return (
    <FieldShell
      error={error}
      htmlFor={`document-type-extension-${field.id}`}
      label={field.label}
      required={field.isRequired}
      requiredLabel={requiredLabel}
    >
      {field.valueType === "dictionary" ? (
        <Select
          disabled={disabled || !field.dictionaryId}
          onValueChange={(nextValue) =>
            onChange(nextValue === NONE_VALUE ? "" : nextValue)
          }
          value={value || NONE_VALUE}
        >
          <SelectTrigger
            aria-invalid={Boolean(error)}
            id={`document-type-extension-${field.id}`}
            className="w-full"
          >
            <SelectValue placeholder={t("dictionaryPlaceholder")} />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectItem value={NONE_VALUE}>{t("none")}</SelectItem>
              {value && !hasCurrentEntry ? (
                <SelectItem value={value}>
                  {fallbackDisplayValue ?? value}
                </SelectItem>
              ) : null}
              {entries.map((entry) => (
                <SelectItem key={entry.id} value={entry.id}>
                  {entry.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      ) : (
        <Input
          aria-invalid={Boolean(error)}
          disabled={disabled}
          id={`document-type-extension-${field.id}`}
          onChange={(event) => onChange(event.target.value)}
          placeholder={field.isRequired ? undefined : t("textPlaceholder")}
          value={value}
        />
      )}
    </FieldShell>
  );
}
