"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PlusIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import {
  CatalogNotice,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { CatalogFormSheetContent } from "@/components/admin/catalog/catalog-form-sheet";
import { UnsavedChangesDialog } from "@/components/admin/catalog/unsaved-changes-dialog";
import { useSheetDismissGuard } from "@/components/ui/sheet-dismiss-guard";
import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import {
  DataListActions,
  DataListContent,
  DataListFilters,
  DataListPanel,
  DataListToolbar,
} from "@/components/ui/data-list";
import {
  DataListChipFilter,
  DataListSearchFilter,
} from "@/components/ui/data-list-filters";
import { Sheet } from "@/components/ui/sheet";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { adminCatalogClient } from "@/lib/admin-settings/api";
import {
  adminCatalogQueryKeys,
  attributeCategoriesQueryOptions,
} from "@/lib/admin-settings/query-options";
import type {
  AttributeCategory,
  CatalogStatusFilter,
  DeleteCatalogEntryResult,
  UpdateAttributeCategoryInput,
  UpsertAttributeCategoryInput,
} from "@/lib/admin-settings/types";
import {
  catalogStatusFilters,
  getCatalogStatusFilterCount,
} from "@/lib/admin-settings/view-model";
import { applyCollectionView, type SortValue } from "@/lib/collection-view";

import {
  AttributeCategoryForm,
  type AttributeCategoryFormMode,
} from "./attribute-category-form";
import { AttributeCategoryTable } from "./attribute-category-table";

type AttributeCategorySaveVariables =
  | {
      input: UpsertAttributeCategoryInput;
      kind: "create";
    }
  | {
      categoryId: string;
      input: UpdateAttributeCategoryInput;
      kind: "edit";
    };

interface AttributeCategoryAction {
  item: AttributeCategory;
  kind: "deactivate" | "delete";
}

const EMPTY_ATTRIBUTE_CATEGORIES: AttributeCategory[] = [];

export function AttributeCategoryCatalog() {
  const t = useTranslations("AdminSettings.attributeCategories");
  const common = useTranslations("AdminSettings.common");
  const collection = useTranslations("CollectionView");
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const [status, setStatus] = useState<CatalogStatusFilter>("active");
  const [formState, setFormState] = useState<AttributeCategoryFormMode | null>(
    null,
  );
  const [formDirty, setFormDirty] = useState(false);
  const [discardOpen, setDiscardOpen] = useState(false);
  const [pendingAction, setPendingAction] =
    useState<AttributeCategoryAction | null>(null);
  const [search, setSearch] = useState("");
  const dismissGuard = useSheetDismissGuard();
  const query = useQuery(attributeCategoriesQueryOptions(status));
  const categories = query.data?.data.categories ?? EMPTY_ATTRIBUTE_CATEGORIES;
  const visibleCategories = useMemo(
    () =>
      applyCollectionView(categories, {
        search,
        searchAccessors: [
          (category): SortValue => category.label,
          (category): SortValue => category.externalId,
        ],
      }),
    [categories, search],
  );
  const hasSearch = search.trim().length > 0;

  const invalidateCategories = async () => {
    await queryClient.invalidateQueries({
      queryKey: adminCatalogQueryKeys.attributeCategories(),
    });
    await queryClient.invalidateQueries({
      queryKey: adminCatalogQueryKeys.attributes(),
    });
  };

  const saveMutation = useMutation({
    mutationFn: (variables: AttributeCategorySaveVariables) =>
      runCsrfProtectedAction((csrfToken) => {
        if (variables.kind === "create") {
          return adminCatalogClient.createAttributeCategory(variables.input, {
            csrfToken,
          });
        }

        return adminCatalogClient.updateAttributeCategory(
          variables.categoryId,
          variables.input,
          { csrfToken },
        );
      }),
    onSuccess: async () => {
      setFormState(null);
      await invalidateCategories();
    },
  });

  const actionMutation = useMutation({
    mutationFn: (action: AttributeCategoryAction) =>
      runCsrfProtectedAction<AttributeCategory | DeleteCatalogEntryResult>(
        (csrfToken) => {
          if (action.kind === "deactivate") {
            return adminCatalogClient.deactivateAttributeCategory(
              action.item.id,
              { csrfToken },
            );
          }

          return adminCatalogClient.deleteAttributeCategory(action.item.id, {
            csrfToken,
          });
        },
      ),
    onSuccess: async () => {
      setPendingAction(null);
      await invalidateCategories();
    },
  });

  function handleSubmit(
    mode: AttributeCategoryFormMode,
    input: UpsertAttributeCategoryInput | UpdateAttributeCategoryInput,
  ) {
    if (mode.kind === "create" && "externalId" in input) {
      saveMutation.mutate({ input, kind: "create" });
      return;
    }

    if (mode.kind === "edit") {
      saveMutation.mutate({
        categoryId: mode.item.id,
        input,
        kind: "edit",
      });
    }
  }

  function handleStatusChange(value: string) {
    if (isCatalogStatusFilter(value)) {
      setStatus(value);
    }
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

  return (
    <section className="flex flex-col gap-5">
      <DataListPanel>
        <DataListToolbar>
          <DataListFilters>
            <DataListChipFilter
              ariaLabel={t("columns.status")}
              onValueChange={handleStatusChange}
              options={catalogStatusFilters.map((filter) => ({
                label: t(`filters.${filter}`, {
                  count: getCatalogStatusFilterCount(query.data?.meta, filter),
                }),
                value: filter,
              }))}
              value={status}
            />

            <DataListSearchFilter
              ariaLabel={collection("search")}
              onValueChange={setSearch}
              placeholder={collection("search")}
              value={search}
            />
          </DataListFilters>

          <DataListActions>
            <Button
              onClick={() => {
                saveMutation.reset();
                setPendingAction(null);
                setFormState({ kind: "create" });
              }}
              size="sm"
            >
              <PlusIcon data-icon="inline-start" />
              {t("create")}
            </Button>
          </DataListActions>
        </DataListToolbar>

        <DataListContent>
          {query.isError ? (
            <CatalogNotice
              description={t("errorDescription")}
              title={getCatalogErrorMessage(query.error, t("errorTitle"))}
              tone="danger"
            />
          ) : null}

          <AttributeCategoryTable
            categories={visibleCategories}
            emptyDescription={
              hasSearch ? collection("noResultsDescription") : undefined
            }
            emptyTitle={hasSearch ? collection("noResults") : undefined}
            isError={query.isError}
            isPending={query.isPending}
            onDeactivate={(category) => {
              actionMutation.reset();
              setFormState(null);
              setPendingAction({ item: category, kind: "deactivate" });
            }}
            onDelete={(category) => {
              actionMutation.reset();
              setFormState(null);
              setPendingAction({ item: category, kind: "delete" });
            }}
            onEdit={(category) => {
              saveMutation.reset();
              setPendingAction(null);
              setFormState({ item: category, kind: "edit" });
            }}
          />
        </DataListContent>
      </DataListPanel>

      <Sheet onOpenChange={handleFormOpenChange} open={Boolean(formState)}>
        <CatalogFormSheetContent>
          {formState ? (
            <AttributeCategoryForm
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

      {pendingAction ? (
        <ConfirmActionDialog
          cancelLabel={common("cancel")}
          confirmLabel={t(`confirm.${pendingAction.kind}.confirm`)}
          description={t(`confirm.${pendingAction.kind}.description`, {
            name: pendingAction.item.label,
          })}
          error={
            actionMutation.error ? (
              <CatalogNotice
                title={getCatalogErrorMessage(
                  actionMutation.error,
                  t("actionFailed"),
                )}
                tone="danger"
              />
            ) : null
          }
          isPending={actionMutation.isPending}
          onConfirm={() => actionMutation.mutate(pendingAction)}
          onOpenChange={(open) => {
            if (!open && !actionMutation.isPending) {
              setPendingAction(null);
            }
          }}
          open
          title={t(`confirm.${pendingAction.kind}.title`)}
        />
      ) : null}
    </section>
  );
}

function isCatalogStatusFilter(value: string): value is CatalogStatusFilter {
  return catalogStatusFilters.some((filter) => filter === value);
}
