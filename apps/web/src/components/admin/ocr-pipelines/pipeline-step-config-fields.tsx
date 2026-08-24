"use client";

import { useTranslations } from "next-intl";

import { CatalogFormSection } from "@/components/admin/catalog/catalog-form-section";
import { FieldShell } from "@/components/admin/catalog/catalog-shared";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldTitle } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { DocumentTypeDisplaySelect } from "@/components/system-catalogs/document-type-display-select";
import { Notice } from "@/components/ui/notice";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  AttributeDefinition,
  DocumentTypeDefinition,
} from "@/lib/admin-settings/types";
import type { SystemCatalogDefinition } from "@/lib/system-catalogs/types";
import type {
  OcrPipelineBlock,
  OcrPipelineConfig,
  OcrPipelineStep,
} from "@/lib/ocr-pipelines/types";
import {
  configString,
  configStringEnum,
  OCR_PIPELINE_NORMALIZATION_STEP_ID,
  presetConfigKey,
  visibleNormalizationAttributes,
  withConfigValue,
  withDocumentTypeId,
  withNormalizationAttributes,
} from "@/lib/ocr-pipelines/view-model";

interface PipelineStepConfigFieldsProps {
  attributes: AttributeDefinition[];
  block: OcrPipelineBlock | undefined;
  documentTypeDefinition: SystemCatalogDefinition | null;
  documentTypes: DocumentTypeDefinition[];
  onUpdate: (config: OcrPipelineConfig) => void;
  selectorCatalogError: string | null;
  selectorCatalogPending: boolean;
  step: OcrPipelineStep;
}

export function PipelineStepConfigFields({
  attributes,
  block,
  documentTypeDefinition,
  documentTypes,
  onUpdate,
  selectorCatalogError,
  selectorCatalogPending,
  step,
}: PipelineStepConfigFieldsProps) {
  const t = useTranslations("AdminOcrPipelines.builder");
  const config = step.config;
  const isNormalization =
    step.implementationId === OCR_PIPELINE_NORMALIZATION_STEP_ID;
  const presetKey = presetConfigKey(config, block);
  const visibleAttributeExternalIds = attributes.map(attributeExternalId);
  const selectedAttributes = new Set(
    visibleNormalizationAttributes(config, visibleAttributeExternalIds),
  );

  return (
    <CatalogFormSection
      className="md:col-span-2"
      contentClassName="grid gap-3 md:grid-cols-2"
      description={t("fields.configurationDescription")}
      title={t("fields.configuration")}
    >
      {presetKey ? (
        <ConfigStringField
          block={block}
          config={config}
          configKey={presetKey}
          inputId={`${step.stepId}-${presetKey}`}
          label={t("fields.preset")}
          onUpdate={onUpdate}
        />
      ) : null}
      {"provider" in config ? (
        <ReadonlyValue
          inputId={`${step.stepId}-provider-readonly`}
          label={t("fields.provider")}
          value={configString(config, "provider")}
        />
      ) : null}
      {"model_id" in config ? (
        <ConfigStringField
          block={block}
          config={config}
          configKey="model_id"
          inputId={`${step.stepId}-model-id`}
          label={t("fields.modelId")}
          onUpdate={onUpdate}
        />
      ) : null}
      {isNormalization ? (
        <NormalizationFields
          attributes={attributes}
          config={config}
          documentTypeDefinition={documentTypeDefinition}
          documentTypes={documentTypes}
          onUpdate={onUpdate}
          selectedAttributes={selectedAttributes}
          selectorCatalogError={selectorCatalogError}
          selectorCatalogPending={selectorCatalogPending}
          stepId={step.stepId}
        />
      ) : null}
      {!block || Object.keys(config).length === 0 ? (
        <p className="text-sm text-muted-foreground md:col-span-2">
          {t("noEditableConfig")}
        </p>
      ) : null}
    </CatalogFormSection>
  );
}

function ConfigStringField({
  block,
  config,
  configKey,
  inputId,
  label,
  onUpdate,
}: {
  block: OcrPipelineBlock | undefined;
  config: OcrPipelineConfig;
  configKey: string;
  inputId: string;
  label: string;
  onUpdate: (config: OcrPipelineConfig) => void;
}) {
  const options = configStringEnum(block, configKey);
  const value = configString(config, configKey);

  if (options.length > 0) {
    return (
      <FieldShell htmlFor={inputId} label={label}>
        <Select
          value={value}
          onValueChange={(next) =>
            onUpdate(withConfigValue(config, configKey, next))
          }
        >
          <SelectTrigger aria-label={label} className="w-full" id={inputId}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {options.map((option) => (
              <SelectItem key={option} value={option}>
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FieldShell>
    );
  }

  return (
    <FieldShell htmlFor={inputId} label={label}>
      <Input
        id={inputId}
        onChange={(event) =>
          onUpdate(withConfigValue(config, configKey, event.target.value))
        }
        value={value}
      />
    </FieldShell>
  );
}

function NormalizationFields({
  attributes,
  config,
  documentTypes,
  documentTypeDefinition,
  onUpdate,
  selectedAttributes,
  selectorCatalogError,
  selectorCatalogPending,
  stepId,
}: {
  attributes: AttributeDefinition[];
  config: OcrPipelineConfig;
  documentTypes: DocumentTypeDefinition[];
  documentTypeDefinition: SystemCatalogDefinition | null;
  onUpdate: (config: OcrPipelineConfig) => void;
  selectedAttributes: Set<string>;
  selectorCatalogError: string | null;
  selectorCatalogPending: boolean;
  stepId: string;
}) {
  const t = useTranslations("AdminOcrPipelines.builder");
  const collection = useTranslations("CollectionView");
  const selectorsDisabled =
    selectorCatalogPending || Boolean(selectorCatalogError);
  const documentTypeId = `${stepId}-normalization-document-type`;

  return (
    <>
      {selectorCatalogPending ? (
        <Notice
          className="md:col-span-2"
          title={t("selectorCatalog.loading")}
        />
      ) : null}
      {selectorCatalogError ? (
        <Notice
          className="md:col-span-2"
          title={selectorCatalogError}
          tone="danger"
        />
      ) : null}
      <FieldShell htmlFor={documentTypeId} label={t("fields.documentType")}>
        <DocumentTypeDisplaySelect
          ariaLabel={t("fields.documentType")}
          definition={documentTypeDefinition}
          disabled={selectorsDisabled}
          displayModeAriaLabel={t("fields.documentTypeDisplayMode")}
          displayModePlaceholder={t("fields.documentTypeDisplayMode")}
          emptyMessage={collection("noResults")}
          id={documentTypeId}
          onValueChange={(value) =>
            onUpdate(withDocumentTypeId(config, value || null))
          }
          options={documentTypes}
          placeholder={t("fields.documentTypePlaceholder")}
          searchPlaceholder={collection("search")}
          triggerClassName="w-full"
          value={configString(config, "document_type_id") || undefined}
        />
      </FieldShell>
      <div className="md:col-span-2">
        <span className="mb-2 block text-sm font-medium">
          {t("fields.attributes")}
        </span>
        <div className="grid gap-2 sm:grid-cols-2">
          {attributes.map((attribute) => {
            const externalId = attribute.externalId ?? attribute.id;
            const checkboxId = `${stepId}-normalization-attribute-${attribute.id}`;

            return (
              <label
                htmlFor={checkboxId}
                className="flex items-center gap-2 rounded-md border bg-background p-2 text-sm"
                key={attribute.id}
              >
                <Checkbox
                  checked={selectedAttributes.has(externalId)}
                  disabled={selectorsDisabled}
                  id={checkboxId}
                  onCheckedChange={(checked) => {
                    const next = new Set(selectedAttributes);
                    if (checked) {
                      next.add(externalId);
                    } else {
                      next.delete(externalId);
                    }
                    onUpdate(withNormalizationAttributes(config, [...next]));
                  }}
                />
                <span>{attribute.name}</span>
              </label>
            );
          })}
        </div>
      </div>
    </>
  );
}

function ReadonlyValue({
  inputId,
  label,
  value,
}: {
  inputId: string;
  label: string;
  value: string;
}) {
  const labelId = `${inputId}-label`;
  const valueId = `${inputId}-value`;

  return (
    <Field>
      <FieldTitle id={labelId}>{label}</FieldTitle>
      <Badge
        aria-labelledby={`${labelId} ${valueId}`}
        className="h-8 rounded-lg px-3 font-mono"
        id={valueId}
        variant="outline"
      >
        {value}
      </Badge>
    </Field>
  );
}

function attributeExternalId(attribute: AttributeDefinition): string {
  return attribute.externalId ?? attribute.id;
}
