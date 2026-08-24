"use client";

import { PlusIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useState, type FormEvent } from "react";

import {
  CatalogFormActions,
  CatalogFormSheet,
  CatalogFormSheetContent,
} from "@/components/admin/catalog/catalog-form-sheet";
import {
  CatalogNotice,
  FieldShell,
} from "@/components/admin/catalog/catalog-shared";
import {
  getInitialFormState,
  type PipelineBuilderTarget,
} from "@/components/admin/ocr-pipelines/pipeline-builder-form-state";
import { PipelineStepEditor } from "@/components/admin/ocr-pipelines/pipeline-step-editor";
import { useUnsavedChangesRegistration } from "@/components/system-catalogs/unsaved-changes-provider";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type {
  AttributeDefinition,
  DocumentTypeDefinition,
} from "@/lib/admin-settings/types";
import type { SystemCatalogDefinition } from "@/lib/system-catalogs/types";
import type {
  CreateOcrPipelineInput,
  OcrPipelineBlock,
  OcrPipelineStep,
} from "@/lib/ocr-pipelines/types";
import {
  createStepFromBlock,
  groupBlocksByCategory,
  hasNormalizationStep,
  moveStep,
  OCR_PIPELINE_NAME_MAX_LENGTH,
  OCR_PIPELINE_STEP_DISPLAY_NAME_MAX_LENGTH,
  prepareStepsForSubmit,
  removeStepAt,
  selectablePipelineBlocks,
  updateStepAt,
} from "@/lib/ocr-pipelines/view-model";

interface PipelineBuilderSheetProps {
  attributes: AttributeDefinition[];
  blocks: OcrPipelineBlock[];
  documentTypeDefinition: SystemCatalogDefinition | null;
  documentTypes: DocumentTypeDefinition[];
  error: string | null;
  existingPipelineNames: string[];
  isPending: boolean;
  onCancel: () => void;
  onSubmit: (input: CreateOcrPipelineInput) => void;
  selectorCatalogError: string | null;
  selectorCatalogPending: boolean;
  target: PipelineBuilderTarget;
}

export function PipelineBuilderSheet({
  attributes,
  blocks,
  documentTypeDefinition,
  documentTypes,
  error,
  existingPipelineNames,
  isPending,
  onCancel,
  onSubmit,
  selectorCatalogError,
  selectorCatalogPending,
  target,
}: PipelineBuilderSheetProps) {
  const t = useTranslations("AdminOcrPipelines.builder");
  const id = useId();
  const initialFormState = getInitialFormState(target, {
    duplicateNameSuffix: t("duplicateNameSuffix"),
    existingPipelineNames,
  });
  const [name, setName] = useState(initialFormState.name);
  const [description, setDescription] = useState(initialFormState.description);
  const [steps, setSteps] = useState<OcrPipelineStep[]>(initialFormState.steps);
  const [selectedBlockId, setSelectedBlockId] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [stepDisplayNameErrors, setStepDisplayNameErrors] = useState<
    Record<string, string>
  >({});
  const [isDirty, setIsDirty] = useState(false);
  useUnsavedChangesRegistration(id, isDirty);
  const selectableBlocks = selectablePipelineBlocks(blocks);
  const blockGroups = groupBlocksByCategory(selectableBlocks);
  const selectedBlock = selectableBlocks.find(
    (block) => block.implementationId === selectedBlockId,
  );
  const requiresSelectorCatalog = hasNormalizationStep(steps);
  const selectorCatalogBlocked = Boolean(
    requiresSelectorCatalog && (selectorCatalogPending || selectorCatalogError),
  );
  const hasStepDisplayNameErrors =
    Object.keys(stepDisplayNameErrors).length > 0;
  const visibleStepError = hasStepDisplayNameErrors
    ? t("errors.stepDisplayNameInvalid")
    : null;
  const visibleFooterError =
    nameError || visibleStepError ? t("errors.fixFields") : error;
  const visibleAttributeExternalIds = attributes.map(attributeExternalId);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedName = name.trim();

    if (!normalizedName) {
      setNameError(t("errors.nameRequired"));
      return;
    }

    if (normalizedName.length > OCR_PIPELINE_NAME_MAX_LENGTH) {
      setNameError(
        t("errors.nameTooLong", { max: OCR_PIPELINE_NAME_MAX_LENGTH }),
      );
      return;
    }

    const nextStepDisplayNameErrors = steps.reduce<Record<string, string>>(
      (errors, step) => {
        const normalizedDisplayName = step.displayName.trim();

        if (!normalizedDisplayName) {
          errors[step.stepId] = t("errors.stepDisplayNameRequired");
        } else if (
          normalizedDisplayName.length >
          OCR_PIPELINE_STEP_DISPLAY_NAME_MAX_LENGTH
        ) {
          errors[step.stepId] = t("errors.stepDisplayNameTooLong", {
            max: OCR_PIPELINE_STEP_DISPLAY_NAME_MAX_LENGTH,
          });
        }

        return errors;
      },
      {},
    );

    if (Object.keys(nextStepDisplayNameErrors).length > 0) {
      setStepDisplayNameErrors(nextStepDisplayNameErrors);
      return;
    }

    if (selectorCatalogBlocked) {
      return;
    }

    setStepDisplayNameErrors({});
    onSubmit({
      description: description.trim() || null,
      name: normalizedName,
      steps: prepareStepsForSubmit(steps, visibleAttributeExternalIds),
    });
  }

  function handleAddStep() {
    if (!selectedBlock || selectedBlock.status !== "available") {
      return;
    }

    setSteps((current) => [
      ...current,
      createStepFromBlock(selectedBlock, current),
    ]);
    setIsDirty(true);
    setSelectedBlockId("");
  }

  function clearStepDisplayNameError(stepId: string) {
    setStepDisplayNameErrors((current) => {
      if (!(stepId in current)) {
        return current;
      }

      const next = { ...current };
      delete next[stepId];

      return next;
    });
  }

  function shouldClearStepDisplayNameError(
    currentStep: OcrPipelineStep,
    nextStep: OcrPipelineStep,
  ): boolean {
    if (nextStep.displayName === currentStep.displayName) {
      return false;
    }

    const normalizedDisplayName = nextStep.displayName.trim();
    return (
      Boolean(normalizedDisplayName) &&
      normalizedDisplayName.length <= OCR_PIPELINE_STEP_DISPLAY_NAME_MAX_LENGTH
    );
  }

  return (
    <CatalogFormSheetContent size="wide">
      <CatalogFormSheet
        description={
          target.kind === "create"
            ? t("createDescription")
            : target.kind === "duplicate"
              ? t("duplicateDescription")
              : t("editDescription")
        }
        footer={
          <CatalogFormActions
            cancelLabel={t("actions.cancel")}
            error={visibleFooterError}
            isPending={isPending}
            onCancel={onCancel}
            saveDisabled={selectorCatalogBlocked}
            saveLabel={t("actions.save")}
            savingLabel={t("actions.saving")}
          />
        }
        onSubmit={handleSubmit}
        title={
          target.kind === "create"
            ? t("createTitle")
            : target.kind === "duplicate"
              ? t("duplicateTitle")
              : t("editTitle")
        }
      >
        <FieldGroup className="gap-4">
          <FieldShell
            error={nameError ?? undefined}
            htmlFor="ocr-pipeline-name"
            label={t("fields.name")}
            required
            requiredLabel={t("fields.requiredField")}
          >
            <Input
              aria-invalid={Boolean(nameError)}
              aria-required="true"
              id="ocr-pipeline-name"
              maxLength={OCR_PIPELINE_NAME_MAX_LENGTH}
              onChange={(event) => {
                setIsDirty(true);
                setName(event.target.value);
                setNameError(null);
              }}
              value={name}
            />
          </FieldShell>
          <FieldShell
            description={t("fields.descriptionDescription")}
            htmlFor="ocr-pipeline-description"
            label={t("fields.description")}
          >
            <Textarea
              id="ocr-pipeline-description"
              onChange={(event) => {
                setIsDirty(true);
                setDescription(event.target.value);
              }}
              value={description}
            />
          </FieldShell>
        </FieldGroup>

        <section className="space-y-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="min-w-0 flex-1">
              <FieldShell
                description={t("fields.blockDescription")}
                htmlFor="ocr-pipeline-block"
                label={t("fields.block")}
              >
                <Select
                  onValueChange={setSelectedBlockId}
                  value={selectedBlockId}
                >
                  <SelectTrigger
                    aria-label={t("fields.block")}
                    className="w-full"
                    id="ocr-pipeline-block"
                  >
                    <SelectValue placeholder={t("fields.blockPlaceholder")} />
                  </SelectTrigger>
                  <SelectContent>
                    {blockGroups.map((group) => (
                      <SelectGroup key={group.category}>
                        <SelectLabel>{group.category}</SelectLabel>
                        {group.blocks.map((block) => (
                          <SelectItem
                            disabled={block.status !== "available"}
                            key={block.implementationId}
                            value={block.implementationId}
                          >
                            <span className="flex min-w-0 items-center gap-2">
                              <span className="truncate">
                                {block.displayName}
                              </span>
                              <span className="shrink-0 text-xs text-muted-foreground">
                                {t(`blockStatus.${block.status}`)}
                              </span>
                            </span>
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    ))}
                  </SelectContent>
                </Select>
              </FieldShell>
            </div>
            <Button
              className="sm:mb-0.5"
              disabled={!selectedBlock || selectedBlock.status !== "available"}
              onClick={handleAddStep}
              type="button"
            >
              <PlusIcon data-icon="inline-start" />
              {t("actions.addStep")}
            </Button>
          </div>

          <div className="grid gap-3">
            {steps.length === 0 ? (
              <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                {t("emptySteps")}
              </div>
            ) : null}
            {steps.map((step, index) => {
              const block = blocks.find(
                (item) => item.implementationId === step.implementationId,
              );

              return (
                <PipelineStepEditor
                  attributes={attributes}
                  block={block}
                  displayNameError={
                    stepDisplayNameErrors[step.stepId] ?? undefined
                  }
                  documentTypeDefinition={documentTypeDefinition}
                  documentTypes={documentTypes}
                  index={index}
                  key={`${step.stepId}-${index}`}
                  onMove={(direction) => {
                    setIsDirty(true);
                    setSteps((current) => moveStep(current, index, direction));
                  }}
                  onRemove={() => {
                    setIsDirty(true);
                    clearStepDisplayNameError(step.stepId);
                    setSteps((current) => removeStepAt(current, index));
                  }}
                  onUpdate={(nextStep) => {
                    setIsDirty(true);
                    if (shouldClearStepDisplayNameError(step, nextStep)) {
                      clearStepDisplayNameError(step.stepId);
                    }
                    setSteps((current) =>
                      updateStepAt(current, index, () => nextStep),
                    );
                  }}
                  selectorCatalogError={selectorCatalogError}
                  selectorCatalogPending={selectorCatalogPending}
                  step={step}
                  stepCount={steps.length}
                />
              );
            })}
          </div>
        </section>

        {requiresSelectorCatalog && selectorCatalogPending ? (
          <CatalogNotice title={t("selectorCatalog.loading")} />
        ) : null}
        {requiresSelectorCatalog && selectorCatalogError ? (
          <CatalogNotice title={selectorCatalogError} tone="danger" />
        ) : null}
        {visibleStepError ? (
          <CatalogNotice title={visibleStepError} tone="danger" />
        ) : null}
      </CatalogFormSheet>
    </CatalogFormSheetContent>
  );
}

function attributeExternalId(attribute: AttributeDefinition): string {
  return attribute.externalId ?? attribute.id;
}
