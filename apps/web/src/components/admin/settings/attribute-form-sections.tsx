"use client";

import { useTranslations } from "next-intl";

import { FieldShell } from "@/components/admin/catalog/catalog-shared";
import { CatalogFormSection } from "@/components/admin/catalog/catalog-form-section";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type {
  AttributeSource,
  AttributeValueSource,
  WritableAttributeDataType,
} from "@/lib/admin-settings/types";
import { attributeSources } from "@/lib/admin-settings/view-model";

import {
  ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH,
  type AttributeFormErrors,
} from "./attribute-form-model";

interface AttributeLlmContextSectionProps {
  isPending: boolean;
  llmContext: string;
  onLlmContextChange: (value: string) => void;
}

export function AttributeLlmContextSection({
  isPending,
  llmContext,
  onLlmContextChange,
}: AttributeLlmContextSectionProps) {
  const t = useTranslations("AdminSettings.attributes.form");

  return (
    <CatalogFormSection
      description={t("llm.description")}
      summary={llmContext.trim() ? t("llm.configured") : t("llm.optional")}
      title={t("llm.title")}
    >
      <FieldShell
        description={t("fields.llmContextDescription")}
        htmlFor="attribute-llm-context"
        label={t("fields.llmContext")}
      >
        <Textarea
          className="min-h-40 resize-y"
          disabled={isPending}
          id="attribute-llm-context"
          maxLength={ATTRIBUTE_LLM_CONTEXT_MAX_LENGTH}
          onChange={(event) => onLlmContextChange(event.target.value)}
          placeholder={t("fields.llmContextPlaceholder")}
          value={llmContext}
        />
      </FieldShell>
    </CatalogFormSection>
  );
}

interface AttributeIntegrationSectionProps {
  comment: string;
  externalId: string;
  isPending: boolean;
  onCommentChange: (value: string) => void;
  onExternalIdChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  source: AttributeSource;
}

export function AttributeIntegrationSection({
  comment,
  externalId,
  isPending,
  onCommentChange,
  onExternalIdChange,
  onSourceChange,
  source,
}: AttributeIntegrationSectionProps) {
  const t = useTranslations("AdminSettings.attributes.form");
  const catalog = useTranslations("AdminSettings.attributes");

  return (
    <CatalogFormSection
      description={t("integration.description")}
      title={t("integration.title")}
    >
      <FieldGroup>
        <FieldShell
          description={t("fields.externalIdDescription")}
          htmlFor="attribute-external-id"
          label={t("fields.externalId")}
        >
          <Input
            disabled={isPending}
            id="attribute-external-id"
            onChange={(event) => onExternalIdChange(event.target.value)}
            placeholder={t("fields.externalIdPlaceholder")}
            value={externalId}
          />
        </FieldShell>

        <Field>
          <FieldLabel>{t("fields.source")}</FieldLabel>
          <FieldDescription>
            {t("integration.sourceDescription")}
          </FieldDescription>
          <ToggleGroup
            aria-label={t("fields.source")}
            onValueChange={onSourceChange}
            type="single"
            value={source}
            variant="outline"
          >
            {attributeSources.map((option) => (
              <ToggleGroupItem
                disabled={isPending}
                key={option}
                size="sm"
                value={option}
              >
                {catalog(`sources.${option}`)}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </Field>

        <FieldShell htmlFor="attribute-comment" label={t("fields.comment")}>
          <Textarea
            disabled={isPending}
            id="attribute-comment"
            onChange={(event) => onCommentChange(event.target.value)}
            value={comment}
          />
        </FieldShell>
      </FieldGroup>
    </CatalogFormSection>
  );
}

interface AttributeValidationSectionProps {
  dataType: WritableAttributeDataType;
  errors: AttributeFormErrors;
  isPending: boolean;
  maxLength: string;
  maxValue: string;
  minLength: string;
  minValue: string;
  onErrorClear: (key: keyof AttributeFormErrors) => void;
  onMaxLengthChange: (value: string) => void;
  onMaxValueChange: (value: string) => void;
  onMinLengthChange: (value: string) => void;
  onMinValueChange: (value: string) => void;
  onPatternChange: (value: string) => void;
  pattern: string;
  valueSource: AttributeValueSource;
}

export function AttributeValidationSection({
  dataType,
  errors,
  isPending,
  maxLength,
  maxValue,
  minLength,
  minValue,
  onErrorClear,
  onMaxLengthChange,
  onMaxValueChange,
  onMinLengthChange,
  onMinValueChange,
  onPatternChange,
  pattern,
  valueSource,
}: AttributeValidationSectionProps) {
  const t = useTranslations("AdminSettings.attributes.form");
  const showTextConstraints =
    dataType === "string" && valueSource !== "dictionary";
  const showNumericConstraints =
    dataType === "integer" || dataType === "number";

  return (
    <CatalogFormSection
      description={t("validation.description")}
      title={t("validation.title")}
    >
      {showTextConstraints ? (
        <FieldGroup>
          <FieldShell
            error={errors.minLength}
            htmlFor="attribute-min-length"
            label={t("fields.minLength")}
          >
            <Input
              aria-invalid={Boolean(errors.minLength)}
              disabled={isPending}
              id="attribute-min-length"
              inputMode="numeric"
              onChange={(event) => {
                onMinLengthChange(event.target.value);
                onErrorClear("minLength");
              }}
              value={minLength}
            />
          </FieldShell>

          <FieldShell
            error={errors.maxLength}
            htmlFor="attribute-max-length"
            label={t("fields.maxLength")}
          >
            <Input
              aria-invalid={Boolean(errors.maxLength)}
              disabled={isPending}
              id="attribute-max-length"
              inputMode="numeric"
              onChange={(event) => {
                onMaxLengthChange(event.target.value);
                onErrorClear("maxLength");
              }}
              value={maxLength}
            />
          </FieldShell>

          <FieldShell htmlFor="attribute-pattern" label={t("fields.pattern")}>
            <Input
              disabled={isPending}
              id="attribute-pattern"
              onChange={(event) => onPatternChange(event.target.value)}
              value={pattern}
            />
          </FieldShell>
        </FieldGroup>
      ) : null}

      {showNumericConstraints ? (
        <FieldGroup>
          <FieldShell
            error={errors.minValue}
            htmlFor="attribute-min-value"
            label={t("fields.minValue")}
          >
            <Input
              aria-invalid={Boolean(errors.minValue)}
              disabled={isPending}
              id="attribute-min-value"
              inputMode="decimal"
              onChange={(event) => {
                onMinValueChange(event.target.value);
                onErrorClear("minValue");
              }}
              value={minValue}
            />
          </FieldShell>

          <FieldShell
            error={errors.maxValue}
            htmlFor="attribute-max-value"
            label={t("fields.maxValue")}
          >
            <Input
              aria-invalid={Boolean(errors.maxValue)}
              disabled={isPending}
              id="attribute-max-value"
              inputMode="decimal"
              onChange={(event) => {
                onMaxValueChange(event.target.value);
                onErrorClear("maxValue");
              }}
              value={maxValue}
            />
          </FieldShell>
        </FieldGroup>
      ) : null}

      {!showTextConstraints && !showNumericConstraints ? (
        <p className="text-sm text-muted-foreground">
          {valueSource === "dictionary"
            ? t("validation.dictionaryOnly")
            : t("validation.noConstraints")}
        </p>
      ) : null}
    </CatalogFormSection>
  );
}
