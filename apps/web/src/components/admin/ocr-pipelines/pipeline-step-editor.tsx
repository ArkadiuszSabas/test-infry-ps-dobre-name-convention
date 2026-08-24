"use client";

import { ArrowDownIcon, ArrowUpIcon, Trash2Icon } from "lucide-react";
import { useTranslations } from "next-intl";

import { FieldShell } from "@/components/admin/catalog/catalog-shared";
import { PipelineStepConfigFields } from "@/components/admin/ocr-pipelines/pipeline-step-config-fields";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldLabel } from "@/components/ui/field";
import { IconTooltipButton } from "@/components/ui/icon-tooltip-button";
import { Input } from "@/components/ui/input";
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
  OcrPipelineStep,
} from "@/lib/ocr-pipelines/types";
import {
  getBlockSummary,
  OCR_PIPELINE_STEP_DISPLAY_NAME_MAX_LENGTH,
} from "@/lib/ocr-pipelines/view-model";

interface StepEditorProps {
  attributes: AttributeDefinition[];
  block: OcrPipelineBlock | undefined;
  displayNameError?: string;
  documentTypeDefinition: SystemCatalogDefinition | null;
  documentTypes: DocumentTypeDefinition[];
  index: number;
  onMove: (direction: -1 | 1) => void;
  onRemove: () => void;
  onUpdate: (step: OcrPipelineStep) => void;
  selectorCatalogError: string | null;
  selectorCatalogPending: boolean;
  step: OcrPipelineStep;
  stepCount: number;
}

export function PipelineStepEditor({
  attributes,
  block,
  displayNameError,
  documentTypeDefinition,
  documentTypes,
  index,
  onMove,
  onRemove,
  onUpdate,
  selectorCatalogError,
  selectorCatalogPending,
  step,
  stepCount,
}: StepEditorProps) {
  const t = useTranslations("AdminOcrPipelines.builder");
  const summary = block ? getBlockSummary(block) : null;
  const enabledId = `ocr-pipeline-step-${step.stepId}-enabled`;
  const failurePolicyId = `ocr-pipeline-step-${step.stepId}-failure-policy`;

  return (
    <div className="rounded-lg border bg-background p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">{index + 1}</Badge>
            <h3 className="truncate text-sm font-semibold">
              {step.displayName}
            </h3>
            {block ? <Badge variant="outline">{block.category}</Badge> : null}
          </div>
          <p className="font-mono text-xs text-muted-foreground">
            {step.implementationId}
          </p>
          {summary ? (
            <p className="text-sm text-muted-foreground">{summary}</p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-1.5">
          <IconTooltipButton
            aria-label={t("actions.moveUp", { number: index + 1 })}
            disabled={index === 0}
            onClick={() => onMove(-1)}
            tooltip={t("actions.moveUp", { number: index + 1 })}
            type="button"
            variant="ghost"
          >
            <ArrowUpIcon />
          </IconTooltipButton>
          <IconTooltipButton
            aria-label={t("actions.moveDown", { number: index + 1 })}
            disabled={index >= stepCount - 1}
            onClick={() => onMove(1)}
            tooltip={t("actions.moveDown", { number: index + 1 })}
            type="button"
            variant="ghost"
          >
            <ArrowDownIcon />
          </IconTooltipButton>
          <IconTooltipButton
            aria-label={t("actions.removeStep", { number: index + 1 })}
            onClick={onRemove}
            tooltip={t("actions.removeStep", { number: index + 1 })}
            type="button"
            variant="ghost"
          >
            <Trash2Icon />
          </IconTooltipButton>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <FieldShell
          error={displayNameError}
          htmlFor={`ocr-pipeline-step-${step.stepId}-display-name`}
          label={t("fields.displayName")}
          required
          requiredLabel={t("fields.requiredField")}
        >
          <Input
            aria-invalid={Boolean(displayNameError)}
            aria-required="true"
            id={`ocr-pipeline-step-${step.stepId}-display-name`}
            maxLength={OCR_PIPELINE_STEP_DISPLAY_NAME_MAX_LENGTH}
            onChange={(event) =>
              onUpdate({ ...step, displayName: event.target.value })
            }
            value={step.displayName}
          />
        </FieldShell>
        <Field orientation="horizontal">
          <Checkbox
            checked={step.enabled}
            id={enabledId}
            onCheckedChange={(checked) =>
              onUpdate({ ...step, enabled: Boolean(checked) })
            }
          />
          <FieldLabel className="font-normal" htmlFor={enabledId}>
            {t("fields.enabled")}
          </FieldLabel>
        </Field>
        <FailurePolicySelect
          block={block}
          inputId={failurePolicyId}
          onUpdate={onUpdate}
          step={step}
        />
        <PipelineStepConfigFields
          attributes={attributes}
          block={block}
          documentTypeDefinition={documentTypeDefinition}
          documentTypes={documentTypes}
          onUpdate={(config) => onUpdate({ ...step, config })}
          selectorCatalogError={selectorCatalogError}
          selectorCatalogPending={selectorCatalogPending}
          step={step}
        />
      </div>
    </div>
  );
}

function FailurePolicySelect({
  block,
  inputId,
  onUpdate,
  step,
}: {
  block: OcrPipelineBlock | undefined;
  inputId: string;
  onUpdate: (step: OcrPipelineStep) => void;
  step: OcrPipelineStep;
}) {
  const t = useTranslations("AdminOcrPipelines");
  const policies = block?.allowedFailurePolicies ?? ["required"];

  return (
    <FieldShell
      description={t("builder.fields.failurePolicyDescription")}
      htmlFor={inputId}
      label={t("builder.fields.failurePolicy")}
    >
      <Select
        value={step.failurePolicy}
        onValueChange={(value) => {
          if (value === "required" || value === "optional") {
            onUpdate({ ...step, failurePolicy: value });
          }
        }}
      >
        <SelectTrigger
          aria-label={t("builder.fields.failurePolicy")}
          className="w-full"
          id={inputId}
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {policies.map((policy) => (
            <SelectItem key={policy} value={policy}>
              {t(`failurePolicy.${policy}`)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FieldShell>
  );
}
