"use client";

import {
  CircleCheckIcon,
  CircleIcon,
  CircleMinusIcon,
  SaveIcon,
  XIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { DocumentTypeDisplayFilter } from "@/components/system-catalogs/document-type-display-filter";
import type { DocumentTypeDefinition } from "@/lib/admin-settings/types";
import type { SystemCatalogDefinition } from "@/lib/system-catalogs/types";
import {
  type AttributeRequirementDraftRow,
  type AttributeRequirementState,
} from "@/lib/admin-settings/view-model";

import { CatalogNotice } from "@/components/admin/catalog/catalog-shared";

const requirementStates = [
  "required",
  "optional",
  "unassigned",
] as const satisfies readonly AttributeRequirementState[];

interface DocumentTypeSelectorProps {
  definition: SystemCatalogDefinition | null;
  documentTypes: DocumentTypeDefinition[];
  isError: boolean;
  isPending: boolean;
  onSelect: (documentTypeId: string) => void;
  selectedDocumentTypeId: string | null;
}

export function DocumentTypeSelector({
  definition,
  documentTypes,
  isError,
  isPending,
  onSelect,
  selectedDocumentTypeId,
}: DocumentTypeSelectorProps) {
  const t = useTranslations("AdminSettings.attributeMatrix");
  const collection = useTranslations("CollectionView");

  function selectDocumentType(documentTypeId: string) {
    if (documentTypeId === selectedDocumentTypeId) {
      return;
    }

    onSelect(documentTypeId);
  }

  if (isPending) {
    return <CatalogNotice title={t("documentTypes.loading")} />;
  }

  if (isError) {
    return (
      <CatalogNotice
        description={t("documentTypes.errorDescription")}
        title={t("documentTypes.errorTitle")}
        tone="danger"
      />
    );
  }

  if (documentTypes.length === 0) {
    return (
      <EmptyState
        className="max-w-xl"
        description={t("documentTypes.emptyDescription")}
        title={t("documentTypes.emptyTitle")}
      />
    );
  }

  return (
    <DocumentTypeDisplayFilter
      ariaLabel={t("documentTypes.label")}
      definition={definition}
      displayModeAriaLabel={t("documentTypes.displayMode")}
      displayModePlaceholder={t("documentTypes.displayMode")}
      emptyMessage={collection("noResults")}
      onValueChange={selectDocumentType}
      options={documentTypes}
      placeholder={t("documentTypes.label")}
      searchPlaceholder={collection("search")}
      triggerClassName="sm:w-80"
      value={selectedDocumentTypeId ?? documentTypes[0]?.id}
    />
  );
}

interface MatrixActionButtonsProps {
  canSave: boolean;
  isDirty: boolean;
  isPending: boolean;
  onReset: () => void;
  onSave: () => void;
}

export function MatrixActionButtons({
  canSave,
  isDirty,
  isPending,
  onReset,
  onSave,
}: MatrixActionButtonsProps) {
  const t = useTranslations("AdminSettings.attributeMatrix");

  return (
    <>
      <Button
        disabled={!isDirty || isPending}
        onClick={onReset}
        size="sm"
        type="button"
        variant="outline"
      >
        <XIcon data-icon="inline-start" />
        {t("actions.reset")}
      </Button>
      <Button disabled={!canSave} onClick={onSave} size="sm" type="button">
        {isPending ? (
          <Spinner data-icon="inline-start" />
        ) : (
          <SaveIcon data-icon="inline-start" />
        )}
        {isPending ? t("actions.saving") : t("actions.save")}
      </Button>
    </>
  );
}

interface RequirementButtonsProps {
  disabled: boolean;
  disableAssign: boolean;
  onChange: (state: AttributeRequirementState) => void;
  row: AttributeRequirementDraftRow;
}

export function RequirementButtons({
  disabled,
  disableAssign,
  onChange,
  row,
}: RequirementButtonsProps) {
  const t = useTranslations("AdminSettings.attributeMatrix");

  return (
    <ToggleGroup
      aria-label={t("columns.requirement")}
      className="flex-wrap justify-start sm:justify-end"
      onValueChange={(value) => {
        if (isAttributeRequirementState(value)) {
          onChange(value);
        }
      }}
      type="single"
      value={row.state}
      variant="outline"
    >
      {requirementStates.map((state) => (
        <ToggleGroupItem
          aria-label={t(`states.${state}`)}
          disabled={disabled || (disableAssign && state !== "unassigned")}
          key={state}
          size={state === "unassigned" ? "default" : "sm"}
          value={state}
        >
          {state === "required" ? (
            <CircleCheckIcon data-icon="inline-start" />
          ) : null}
          {state === "optional" ? (
            <CircleIcon data-icon="inline-start" />
          ) : null}
          {state === "unassigned" ? (
            <>
              <CircleMinusIcon data-icon="inline-start" />
              <span className="sr-only">{t(`states.${state}`)}</span>
            </>
          ) : (
            t(`states.${state}`)
          )}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}

function isAttributeRequirementState(
  value: string,
): value is AttributeRequirementState {
  return requirementStates.some((state) => state === value);
}
