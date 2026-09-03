"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useId, useMemo, useState } from "react";

import { useUnsavedChangesRegistration } from "@/components/system-catalogs/unsaved-changes-provider";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import { adminCatalogClient } from "@/lib/admin-settings/api";
import { updateAttributeRequirementMatrixCache } from "@/lib/admin-settings/attribute-requirements-cache";
import {
  adminCatalogQueryKeys,
  attributeRequirementsQueryOptions,
  documentTypesQueryOptions,
} from "@/lib/admin-settings/query-options";
import type {
  AttributeDefinition,
  AttributeRequirementMatrixEnvelope,
} from "@/lib/admin-settings/types";
import { systemCatalogDefinitionQueryOptions } from "@/lib/system-catalogs/query-options";
import {
  buildAttributeRequirementDraftRows,
  getDuplicateAttributeRequirementIds,
  getAttributeRequirementCategoryOptions,
  getAttributeRequirementDraftMetrics,
  getAttributeRequirementErrorMap,
  getInactiveAssignedAttributeIds,
  hasAttributeRequirementDraftChanges,
  toSaveAttributeRequirementInput,
} from "@/lib/admin-settings/view-model";
import type {
  AttributeRequirementDraftRow,
  AttributeRequirementState,
} from "@/lib/admin-settings/view-model";

import {
  CatalogNotice,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { AttributeMatrixTable } from "./attribute-matrix-table";
import { AttributeEditDrawer } from "./attribute-edit-drawer";
import {
  ALL_ATTRIBUTE_CATEGORIES_VALUE,
  AttributeMatrixToolbar,
  attributeMatrixRequirementFilters,
  type AttributeMatrixRequirementFilter,
} from "./attribute-matrix-toolbar";

interface AttributeMatrixEditorProps {
  initialDocumentTypeId?: string | null;
}

export function AttributeMatrixEditor({
  initialDocumentTypeId = null,
}: AttributeMatrixEditorProps) {
  const t = useTranslations("AdminSettings.attributeMatrix");
  const collection = useTranslations("CollectionView");
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const documentTypesQuery = useQuery(documentTypesQueryOptions("all"));
  const documentTypeDefinitionQuery = useQuery(
    systemCatalogDefinitionQueryOptions("document_type"),
  );
  const documentTypes = useMemo(
    () => documentTypesQuery.data?.data.documentTypes ?? [],
    [documentTypesQuery.data],
  );
  const [selectedDocumentTypeId, setSelectedDocumentTypeId] = useState<
    string | null
  >(initialDocumentTypeId);
  const [requirementFilter, setRequirementFilter] =
    useState<AttributeMatrixRequirementFilter>("all");
  const [attributeCategoryFilter, setAttributeCategoryFilter] = useState(
    ALL_ATTRIBUTE_CATEGORIES_VALUE,
  );
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState<{
    documentTypeId: string;
    rows: AttributeRequirementDraftRow[];
  } | null>(null);
  const [pendingDocumentTypeId, setPendingDocumentTypeId] = useState<
    string | null
  >(null);
  const [editAttributeId, setEditAttributeId] = useState<string | null>(null);

  const selectedDocumentType = useMemo(
    () =>
      documentTypes.find(
        (documentType) => documentType.id === selectedDocumentTypeId,
      ) ??
      documentTypes[0] ??
      null,
    [documentTypes, selectedDocumentTypeId],
  );
  const effectiveDocumentTypeId = selectedDocumentType?.id ?? null;
  const hasSelectedDocumentType = Boolean(effectiveDocumentTypeId);
  const matrixQuery = useQuery(
    attributeRequirementsQueryOptions(effectiveDocumentTypeId),
  );
  const baselineRows = useMemo(
    () =>
      matrixQuery.data
        ? buildAttributeRequirementDraftRows(matrixQuery.data.data)
        : [],
    [matrixQuery.data],
  );
  const rows =
    draft?.documentTypeId === effectiveDocumentTypeId
      ? draft.rows
      : baselineRows;

  const saveMutation = useMutation({
    mutationFn: (variables: {
      documentTypeId: string;
      rows: readonly AttributeRequirementDraftRow[];
    }) =>
      runCsrfProtectedAction((csrfToken) =>
        adminCatalogClient.saveAttributeRequirements(
          variables.documentTypeId,
          toSaveAttributeRequirementInput(variables.rows),
          { csrfToken },
        ),
      ),
    onSuccess: async (result, variables) => {
      setDraft(null);
      queryClient.setQueryData(
        adminCatalogQueryKeys.attributeRequirementsDetail(
          variables.documentTypeId,
        ),
        result,
      );
      await queryClient.invalidateQueries({
        queryKey: adminCatalogQueryKeys.attributeRequirements(),
      });
    },
  });

  const matrixDocumentType =
    matrixQuery.data?.data.documentType ?? selectedDocumentType ?? null;
  const metrics = useMemo(
    () => getAttributeRequirementDraftMetrics(rows),
    [rows],
  );
  const requirementMetricCount = useMemo(
    () =>
      Object.fromEntries(
        metrics.map((metric) => [metric.id, metric.value]),
      ) as Record<string, number>,
    [metrics],
  );
  const attributeCategoryOptions = useMemo(
    () => getAttributeRequirementCategoryOptions(rows),
    [rows],
  );
  const effectiveAttributeCategoryFilter =
    attributeCategoryFilter === ALL_ATTRIBUTE_CATEGORIES_VALUE ||
    attributeCategoryOptions.some(
      (option) => option.category === attributeCategoryFilter,
    )
      ? attributeCategoryFilter
      : ALL_ATTRIBUTE_CATEGORIES_VALUE;
  const duplicateIds = useMemo(
    () => getDuplicateAttributeRequirementIds(rows),
    [rows],
  );
  const inactiveAssignedIds = useMemo(
    () => getInactiveAssignedAttributeIds(rows, matrixDocumentType),
    [matrixDocumentType, rows],
  );
  const backendErrorMap = useMemo(
    () => getAttributeRequirementErrorMap(saveMutation.error),
    [saveMutation.error],
  );
  const blockingRowIds = useMemo(
    () =>
      new Set([
        ...duplicateIds,
        ...inactiveAssignedIds,
        ...Object.keys(backendErrorMap),
      ]),
    [backendErrorMap, duplicateIds, inactiveAssignedIds],
  );
  const normalizedSearch = search.trim().toLocaleLowerCase();
  const visibleRows = useMemo(
    () =>
      rows.filter((row) => {
        if (blockingRowIds.has(row.attribute.id)) {
          return true;
        }

        const matchesRequirement =
          requirementFilter === "all" || row.state === requirementFilter;
        const matchesCategory =
          effectiveAttributeCategoryFilter === ALL_ATTRIBUTE_CATEGORIES_VALUE ||
          row.attribute.category === effectiveAttributeCategoryFilter;
        const matchesSearch =
          !normalizedSearch ||
          [
            row.attribute.name,
            row.attribute.externalId,
            row.attribute.category,
            row.attribute.status,
          ].some((value) =>
            value?.toLocaleLowerCase().includes(normalizedSearch),
          );

        return matchesRequirement && matchesCategory && matchesSearch;
      }),
    [
      blockingRowIds,
      effectiveAttributeCategoryFilter,
      normalizedSearch,
      requirementFilter,
      rows,
    ],
  );
  const hasActiveMatrixFilters =
    requirementFilter !== "all" ||
    effectiveAttributeCategoryFilter !== ALL_ATTRIBUTE_CATEGORIES_VALUE ||
    normalizedSearch.length > 0;
  const isDirty = useMemo(
    () =>
      draft?.documentTypeId === effectiveDocumentTypeId &&
      hasAttributeRequirementDraftChanges(rows, baselineRows),
    [baselineRows, draft?.documentTypeId, effectiveDocumentTypeId, rows],
  );
  const unknownBackendIds = Object.keys(backendErrorMap).filter(
    (attributeId) => !rows.some((row) => row.attribute.id === attributeId),
  );
  const hasBlockingErrors =
    duplicateIds.length > 0 || inactiveAssignedIds.length > 0;
  const isMatrixPending = hasSelectedDocumentType && matrixQuery.isPending;
  const isMatrixError = hasSelectedDocumentType && matrixQuery.isError;
  const canSave =
    hasSelectedDocumentType &&
    isDirty &&
    !hasBlockingErrors &&
    !isMatrixPending &&
    !saveMutation.isPending;
  const unsavedChangesId = useId();
  useUnsavedChangesRegistration(unsavedChangesId, isDirty);

  function selectDocumentType(documentTypeId: string) {
    if (documentTypeId === effectiveDocumentTypeId) {
      return;
    }

    if (isDirty) {
      setPendingDocumentTypeId(documentTypeId);
      return;
    }

    applyDocumentType(documentTypeId);
  }

  function applyDocumentType(documentTypeId: string) {
    saveMutation.reset();
    setDraft(null);
    setSelectedDocumentTypeId(documentTypeId);
  }

  function handleRequirementFilterChange(value: string) {
    if (isAttributeMatrixRequirementFilter(value)) {
      setRequirementFilter(value);
    }
  }

  function updateRowState(
    attributeId: string,
    state: AttributeRequirementState,
  ) {
    saveMutation.reset();
    if (!effectiveDocumentTypeId) {
      return;
    }

    setDraft({
      documentTypeId: effectiveDocumentTypeId,
      rows: rows.map((row) =>
        row.attribute.id === attributeId ? { ...row, state } : row,
      ),
    });
  }

  function updateMetadataInclusion(attributeId: string, checked: boolean) {
    saveMutation.reset();
    if (!effectiveDocumentTypeId) {
      return;
    }
    setDraft({
      documentTypeId: effectiveDocumentTypeId,
      rows: rows.map((row) =>
        row.attribute.id === attributeId
          ? { ...row, includeMetadataInContextResolver: checked }
          : row,
      ),
    });
  }

  function resetDraft() {
    saveMutation.reset();
    setDraft(null);
  }

  function applyAttributeUpdate(
    attribute: AttributeDefinition,
    isMetadata: boolean,
  ) {
    const updateDraftAttribute = (row: AttributeRequirementDraftRow) =>
      row.attribute.id === attribute.id
        ? {
            ...row,
            attribute: {
              ...row.attribute,
              category: attribute.category,
              externalId: attribute.externalId,
              isMetadata,
              name: attribute.name,
              status: attribute.status,
            },
            includeMetadataInContextResolver: isMetadata
              ? row.includeMetadataInContextResolver
              : false,
          }
        : row;

    setDraft((current) =>
      current?.documentTypeId === effectiveDocumentTypeId
        ? { ...current, rows: current.rows.map(updateDraftAttribute) }
        : current,
    );

    if (effectiveDocumentTypeId) {
      queryClient.setQueryData<AttributeRequirementMatrixEnvelope>(
        adminCatalogQueryKeys.attributeRequirementsDetail(
          effectiveDocumentTypeId,
        ),
        (current) =>
          current
            ? updateAttributeRequirementMatrixCache(
                current,
                attribute,
                isMetadata,
              )
            : current,
      );
    }
  }

  function discardChangesAndChangeDocumentType() {
    const documentTypeId = pendingDocumentTypeId;
    setPendingDocumentTypeId(null);

    if (documentTypeId) {
      applyDocumentType(documentTypeId);
    }
  }

  function saveDraft() {
    if (!effectiveDocumentTypeId) {
      return;
    }

    saveMutation.mutate({
      documentTypeId: effectiveDocumentTypeId,
      rows,
    });
  }

  return (
    <section className="flex flex-col gap-5">
      <AttributeMatrixToolbar
        attributeCategoryFilter={effectiveAttributeCategoryFilter}
        attributeCategoryOptions={attributeCategoryOptions}
        canSave={canSave}
        definition={documentTypeDefinitionQuery.data ?? null}
        documentTypes={documentTypes}
        documentTypesError={documentTypesQuery.isError}
        documentTypesPending={documentTypesQuery.isPending}
        isDirty={isDirty}
        isSaving={saveMutation.isPending}
        onAttributeCategoryFilterChange={setAttributeCategoryFilter}
        onRequirementFilterChange={handleRequirementFilterChange}
        onReset={resetDraft}
        onSave={saveDraft}
        onSearchChange={setSearch}
        onSelectDocumentType={selectDocumentType}
        requirementFilter={requirementFilter}
        requirementMetricCount={requirementMetricCount}
        rowsCount={rows.length}
        search={search}
        selectedDocumentTypeId={effectiveDocumentTypeId}
      />

      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-4">
          {isMatrixError ? (
            <CatalogNotice
              description={t("errors.loadDescription")}
              title={getCatalogErrorMessage(
                matrixQuery.error,
                t("errors.loadFailed"),
              )}
              tone="danger"
            />
          ) : null}

          {saveMutation.error ? (
            <CatalogNotice
              description={
                unknownBackendIds.length > 0
                  ? t("errors.unknownBackendIds", {
                      ids: unknownBackendIds.join(", "),
                    })
                  : t("errors.inlineHint")
              }
              title={getCatalogErrorMessage(
                saveMutation.error,
                t("errors.saveFailed"),
              )}
              tone="danger"
            />
          ) : null}

          {hasSelectedDocumentType ? (
            <AttributeMatrixTable
              backendErrorMap={backendErrorMap}
              duplicateIds={duplicateIds}
              emptyDescription={
                hasActiveMatrixFilters
                  ? collection("noResultsDescription")
                  : undefined
              }
              emptyTitle={
                hasActiveMatrixFilters ? collection("noResults") : undefined
              }
              inactiveAssignedIds={inactiveAssignedIds}
              isError={isMatrixError}
              isPending={isMatrixPending}
              isSaving={saveMutation.isPending}
              matrixDocumentType={matrixDocumentType}
              onEdit={setEditAttributeId}
              onStateChange={updateRowState}
              onMetadataInclusionChange={updateMetadataInclusion}
              rows={visibleRows}
            />
          ) : null}
        </div>
      </div>

      <ConfirmActionDialog
        cancelLabel={t("documentTypes.discardChanges.stay")}
        confirmLabel={t("documentTypes.discardChanges.discard")}
        description={t("documentTypes.discardChanges.description")}
        isPending={false}
        onConfirm={discardChangesAndChangeDocumentType}
        onOpenChange={(open) => {
          if (!open) setPendingDocumentTypeId(null);
        }}
        open={pendingDocumentTypeId !== null}
        title={t("documentTypes.discardChanges.title")}
      />

      <AttributeEditDrawer
        attributeId={editAttributeId}
        onClose={() => setEditAttributeId(null)}
        onSaved={applyAttributeUpdate}
      />
    </section>
  );
}

function isAttributeMatrixRequirementFilter(
  value: string,
): value is AttributeMatrixRequirementFilter {
  return attributeMatrixRequirementFilters.some((filter) => filter === value);
}
