"use client";

import { useTranslations } from "next-intl";

import { FieldShell } from "@/components/admin/catalog/catalog-shared";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type {
  AttributeValueSource,
  CustomDictionary,
  WritableAttributeDataType,
} from "@/lib/admin-settings/types";
import {
  attributeDataTypes,
  attributeValueSources,
} from "@/lib/admin-settings/view-model";

interface AttributeValueSourceFieldsProps {
  dataType: WritableAttributeDataType;
  dictionaryError?: string;
  dictionaryId: string;
  dictionaries: CustomDictionary[];
  dictionariesLoading: boolean;
  isPending: boolean;
  onDataTypeChange: (value: string) => void;
  onDictionaryChange: (value: string) => void;
  onValueSourceChange: (value: string) => void;
  valueSource: AttributeValueSource;
}

export function AttributeValueSourceFields({
  dataType,
  dictionaryError,
  dictionaryId,
  dictionaries,
  dictionariesLoading,
  isPending,
  onDataTypeChange,
  onDictionaryChange,
  onValueSourceChange,
  valueSource,
}: AttributeValueSourceFieldsProps) {
  const t = useTranslations("AdminSettings.attributes.form");
  const catalog = useTranslations("AdminSettings.attributes");
  const common = useTranslations("AdminSettings.common");
  const collection = useTranslations("CollectionView");

  return (
    <>
      <Field>
        <FieldLabel>{t("fields.valueSource")}</FieldLabel>
        <FieldDescription>{t("valueSource.description")}</FieldDescription>
        <ToggleGroup
          aria-label={t("fields.valueSource")}
          className="flex-wrap justify-start"
          onValueChange={onValueSourceChange}
          type="single"
          value={valueSource}
          variant="outline"
        >
          {attributeValueSources.map((option) => (
            <ToggleGroupItem
              disabled={isPending}
              key={option}
              size="sm"
              value={option}
            >
              {catalog(`valueSources.${option}`)}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </Field>

      {valueSource === "free_text" ? (
        <Field>
          <FieldLabel>{t("fields.dataType")}</FieldLabel>
          <FieldDescription>{t("valueSource.freeTextHint")}</FieldDescription>
          <ToggleGroup
            aria-label={t("fields.dataType")}
            className="flex-wrap justify-start"
            onValueChange={onDataTypeChange}
            type="single"
            value={dataType}
            variant="outline"
          >
            {attributeDataTypes.map((option) => (
              <ToggleGroupItem
                disabled={isPending}
                key={option}
                size="sm"
                value={option}
              >
                {catalog(`dataTypes.${option}`)}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </Field>
      ) : null}

      {valueSource === "dictionary" ? (
        <FieldShell
          error={dictionaryError}
          htmlFor="attribute-dictionary"
          label={t("fields.dictionary")}
          required
          requiredLabel={common("requiredField")}
        >
          <SearchableSelect
            ariaLabel={t("fields.dictionary")}
            disabled={isPending || dictionariesLoading}
            emptyMessage={collection("noResults")}
            id="attribute-dictionary"
            invalid={Boolean(dictionaryError)}
            onValueChange={onDictionaryChange}
            options={dictionaries.map((dictionary) => ({
              label: `${dictionary.name} - ${dictionary.externalId}`,
              value: dictionary.id,
            }))}
            placeholder={t("fields.dictionaryPlaceholder")}
            searchPlaceholder={collection("search")}
            triggerClassName="w-full"
            value={dictionaryId || undefined}
          />
        </FieldShell>
      ) : null}
    </>
  );
}
