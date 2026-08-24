"use client";

import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { CatalogFormSheetContent } from "@/components/admin/catalog/catalog-form-sheet";
import { UnsavedChangesDialog } from "@/components/admin/catalog/unsaved-changes-dialog";
import { useSheetDismissGuard } from "@/components/ui/sheet-dismiss-guard";
import { DataListPanel } from "@/components/ui/data-list";
import { Sheet } from "@/components/ui/sheet";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { adminCatalogClient } from "@/lib/admin-settings/api";
import {
  adminCatalogQueryKeys,
  attributesQueryOptions,
  dictionariesQueryOptions,
  dictionaryEntryLookupQueryOptions,
  documentTypesQueryOptions,
} from "@/lib/admin-settings/query-options";
import type {
  CatalogStatusFilter,
  DeleteCatalogEntryResult,
  DocumentTypeDefinition,
  SaveSystemCatalogDefinitionInput,
  UpsertDocumentTypeInput,
} from "@/lib/admin-settings/types";
import {
  catalogStatusFilters,
  filterDocumentTypesByParameterFilters,
  getActiveSystemCatalogFields,
  getDocumentTypeParameterFilters,
  getSystemCatalogExtensionDictionaryIds,
  hasActiveDocumentTypeParameterFilters,
  normalizeDocumentTypeParameterFilterValues,
} from "@/lib/admin-settings/view-model";
import {
  systemCatalogDefinitionQueryOptions,
  systemCatalogQueryKeys,
} from "@/lib/system-catalogs/query-options";

import {
  DocumentTypeActionDialog,
  type DocumentTypeAction,
} from "./document-type-action-dialog";
import { DocumentTypeCatalogContent } from "./document-type-catalog-content";
import { DocumentTypeCatalogToolbar } from "./document-type-catalog-toolbar";
import {
  getVisibleDocumentTypes,
  type DocumentTypeFormState,
  type DocumentTypeSaveVariables,
} from "./document-type-catalog-view-model";
import { DocumentTypeDefinitionDrawer } from "./document-type-definition-drawer";
import { DocumentTypeForm } from "./document-type-form";

const EMPTY_DOCUMENT_TYPES: DocumentTypeDefinition[] = [];

export function DocumentTypeCatalog() {
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [status, setStatus] = useState<CatalogStatusFilter>("active");
  const [formState, setFormState] = useState<DocumentTypeFormState | null>(
    null,
  );
  const [formDirty, setFormDirty] = useState(false);
  const [discardOpen, setDiscardOpen] = useState(false);
  const [definitionOpen, setDefinitionOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<DocumentTypeAction | null>(
    null,
  );
  const [search, setSearch] = useState("");
  const dismissGuard = useSheetDismissGuard();
  const [parameterFilterValues, setParameterFilterValues] = useState<
    Record<string, string | null>
  >({});
  const query = useQuery(documentTypesQueryOptions(status));
  const activeTypesQuery = useQuery(documentTypesQueryOptions("active"));
  const definitionQuery = useQuery(
    systemCatalogDefinitionQueryOptions("document_type"),
  );
  const dictionariesQuery = useQuery(dictionariesQueryOptions("active", null));
  const attributesQuery = useQuery(attributesQueryOptions(null));
  const documentTypes = query.data?.data.documentTypes ?? EMPTY_DOCUMENT_TYPES;
  const parameterFilters = useMemo(
    () => getDocumentTypeParameterFilters(documentTypes),
    [documentTypes],
  );
  const activeParameterFilterValues = useMemo(
    () =>
      normalizeDocumentTypeParameterFilterValues(
        parameterFilters,
        parameterFilterValues,
      ),
    [parameterFilterValues, parameterFilters],
  );
  const filteredDocumentTypes = useMemo(
    () =>
      filterDocumentTypesByParameterFilters(
        documentTypes,
        activeParameterFilterValues,
      ),
    [activeParameterFilterValues, documentTypes],
  );
  const activeDocumentTypes =
    activeTypesQuery.data?.data.documentTypes ?? EMPTY_DOCUMENT_TYPES;
  const definition = definitionQuery.data ?? null;
  const visibleDocumentTypes = useMemo(
    () =>
      getVisibleDocumentTypes({
        documentTypes: filteredDocumentTypes,
        search,
      }),
    [filteredDocumentTypes, search],
  );
  const hasSearch = search.trim().length > 0;
  const hasActiveFilters =
    hasSearch ||
    hasActiveDocumentTypeParameterFilters(activeParameterFilterValues);
  const activeFields = getActiveSystemCatalogFields(definition?.fields ?? []);
  const extensionDictionaryIds =
    getSystemCatalogExtensionDictionaryIds(activeFields);
  const dictionaryEntryQueries = useQueries({
    queries: extensionDictionaryIds.map((dictionaryId) =>
      dictionaryEntryLookupQueryOptions(dictionaryId, Boolean(definition)),
    ),
  });
  const dictionaryEntriesByDictionaryId = Object.fromEntries(
    extensionDictionaryIds.map((dictionaryId, index) => [
      dictionaryId,
      dictionaryEntryQueries[index]?.data?.data.entries ?? [],
    ]),
  );
  const dictionaryEntriesError =
    dictionaryEntryQueries.find((entryQuery) => entryQuery.isError)?.error ??
    null;
  const dictionaryEntriesPending = dictionaryEntryQueries.some(
    (entryQuery) => entryQuery.isPending,
  );
  const activeDictionaries =
    dictionariesQuery.data?.data.dictionaries.filter(
      (dictionary) => dictionary.status === "active",
    ) ?? [];
  const activeAttributes =
    attributesQuery.data?.data.attributes.filter(
      (attribute) => attribute.status === "active",
    ) ?? [];

  const invalidateDocumentTypes = async () => {
    await queryClient.invalidateQueries({
      queryKey: adminCatalogQueryKeys.documentTypes(),
    });
    await queryClient.invalidateQueries({
      queryKey: systemCatalogQueryKeys.options("document_type"),
    });
  };

  const saveMutation = useMutation({
    mutationFn: (variables: DocumentTypeSaveVariables) =>
      runCsrfProtectedAction((csrfToken) => {
        if (variables.kind === "create") {
          return adminCatalogClient.createDocumentType(variables.input, {
            csrfToken,
          });
        }

        return adminCatalogClient.updateDocumentType(
          variables.documentTypeId,
          variables.input,
          { csrfToken },
        );
      }),
    onSuccess: async () => {
      setFormState(null);
      await invalidateDocumentTypes();
    },
  });

  const actionMutation = useMutation({
    mutationFn: (action: DocumentTypeAction) =>
      runCsrfProtectedAction<DocumentTypeDefinition | DeleteCatalogEntryResult>(
        (csrfToken) => {
          if (action.kind === "deactivate") {
            return adminCatalogClient.deactivateDocumentType(action.item.id, {
              csrfToken,
            });
          }

          return adminCatalogClient.deleteDocumentType(action.item.id, {
            csrfToken,
          });
        },
      ),
    onSuccess: async () => {
      setPendingAction(null);
      await invalidateDocumentTypes();
    },
  });

  const definitionMutation = useMutation({
    mutationFn: (input: SaveSystemCatalogDefinitionInput) =>
      runCsrfProtectedAction((csrfToken) =>
        adminCatalogClient.saveSystemCatalogDefinition("document_type", input, {
          csrfToken,
        }),
      ),
    onSuccess: async (result) => {
      queryClient.setQueryData(
        systemCatalogQueryKeys.definition("document_type"),
        result,
      );
      setDefinitionOpen(false);
      await invalidateDocumentTypes();
    },
  });

  function handleSubmit(
    mode: DocumentTypeFormState,
    input: UpsertDocumentTypeInput,
  ) {
    if (mode.kind === "create") {
      saveMutation.mutate({
        input,
        kind: "create",
      });
      return;
    }

    saveMutation.mutate({
      documentTypeId: mode.item.id,
      input: {
        description: input.description,
        ...(input.extensionValues
          ? { extensionValues: input.extensionValues }
          : {}),
        name: input.name,
      },
      kind: "edit",
    });
  }

  function openEditForm(documentType: DocumentTypeDefinition) {
    saveMutation.reset();
    setPendingAction(null);
    setFormState({ item: documentType, kind: "edit" });
  }

  function openEditFormFromDefinition(documentType: DocumentTypeDefinition) {
    definitionMutation.reset();
    saveMutation.reset();
    setPendingAction(null);
    setFormState({ item: documentType, kind: "edit" });
  }

  function openPendingAction(
    documentType: DocumentTypeDefinition,
    kind: DocumentTypeAction["kind"],
  ) {
    actionMutation.reset();
    setFormState(null);
    setPendingAction({ item: documentType, kind });
  }

  function handleStatusChange(value: string) {
    if (catalogStatusFilters.some((filter) => filter === value)) {
      setStatus(value as CatalogStatusFilter);
    }
  }

  function handleParameterFilterChange(code: string, value: string | null) {
    setParameterFilterValues((current) => ({
      ...current,
      [code]: value,
    }));
  }

  function closeForm() {
    if (!saveMutation.isPending) {
      saveMutation.reset();
      setFormState(null);
      setFormDirty(false);
    }
  }

  function discardChanges() {
    setDiscardOpen(false);
    closeForm();
  }

  function handleFormOpenChange(open: boolean) {
    if (!open && !saveMutation.isPending) {
      if (dismissGuard?.isDiscardingRef.current) {
        closeForm();
        return;
      }
      if (formDirty) setDiscardOpen(true);
      else closeForm();
    }
  }

  function handleDefinitionOpenChange(open: boolean) {
    if (!open && definitionMutation.isPending) {
      return;
    }

    setDefinitionOpen(open);

    if (!open) {
      definitionMutation.reset();
    }
  }

  return (
    <section className="flex flex-col gap-5">
      <DataListPanel>
        <DocumentTypeCatalogToolbar
          onConfigureDefinition={() => {
            definitionMutation.reset();
            setPendingAction(null);
            setFormState(null);
            setDefinitionOpen(true);
          }}
          onCreate={() => {
            saveMutation.reset();
            setPendingAction(null);
            setFormState({ kind: "create" });
          }}
          onParameterFilterChange={handleParameterFilterChange}
          onSearchChange={setSearch}
          onStatusChange={handleStatusChange}
          parameterFilterValues={activeParameterFilterValues}
          parameterFilters={parameterFilters}
          search={search}
          status={status}
          statusMeta={query.data?.meta}
        />

        <DocumentTypeCatalogContent
          documentTypes={documentTypes}
          hasActiveFilters={hasActiveFilters}
          isError={query.isError}
          isPending={query.isPending}
          loadError={query.error}
          onDeactivate={(item) => openPendingAction(item, "deactivate")}
          onDelete={(item) => openPendingAction(item, "delete")}
          onEdit={openEditForm}
          visibleDocumentTypes={visibleDocumentTypes}
        />
      </DataListPanel>

      <Sheet onOpenChange={handleDefinitionOpenChange} open={definitionOpen}>
        <CatalogFormSheetContent size="wide">
          <DocumentTypeDefinitionDrawer
            activeAttributes={activeAttributes}
            activeDictionaries={activeDictionaries}
            definition={definition}
            documentTypes={activeDocumentTypes}
            error={definitionMutation.error}
            isLoading={
              definitionQuery.isPending ||
              dictionariesQuery.isPending ||
              attributesQuery.isPending ||
              activeTypesQuery.isPending
            }
            isPending={definitionMutation.isPending}
            key={`${definitionOpen ? "open" : "closed"}-${definitionQuery.dataUpdatedAt}`}
            loadError={
              definitionQuery.error ??
              dictionariesQuery.error ??
              attributesQuery.error ??
              activeTypesQuery.error
            }
            onCancel={() => handleDefinitionOpenChange(false)}
            onEditDocumentType={openEditFormFromDefinition}
            onSubmit={(input) => definitionMutation.mutate(input)}
          />
        </CatalogFormSheetContent>
      </Sheet>

      <Sheet onOpenChange={handleFormOpenChange} open={Boolean(formState)}>
        <CatalogFormSheetContent>
          {formState ? (
            <DocumentTypeForm
              definition={definition}
              definitionError={definitionQuery.error}
              dictionaryEntriesByDictionaryId={dictionaryEntriesByDictionaryId}
              dictionaryEntriesError={dictionaryEntriesError}
              dictionaryEntriesPending={dictionaryEntriesPending}
              error={saveMutation.error}
              isPending={saveMutation.isPending}
              key={
                formState.kind === "create"
                  ? "create"
                  : `edit-${formState.item.id}`
              }
              mode={formState}
              onCancel={() => handleFormOpenChange(false)}
              onDirtyChange={setFormDirty}
              onSubmit={handleSubmit}
            />
          ) : null}
        </CatalogFormSheetContent>
      </Sheet>

      <UnsavedChangesDialog
        onDiscard={discardChanges}
        onOpenChange={setDiscardOpen}
        open={discardOpen}
      />

      <DocumentTypeActionDialog
        action={pendingAction}
        error={actionMutation.error}
        isPending={actionMutation.isPending}
        onConfirm={(action) => actionMutation.mutate(action)}
        onOpenChange={(open) => {
          if (!open && !actionMutation.isPending) {
            setPendingAction(null);
          }
        }}
      />
    </section>
  );
}
